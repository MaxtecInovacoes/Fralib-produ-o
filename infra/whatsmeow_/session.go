package main

import (
	"context"
	"database/sql"
	"encoding/base64"
	"fmt"
	"log"
	"os"
	"sync"
	"time"

	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/store"
	"go.mau.fi/whatsmeow/store/sqlstore"
	"go.mau.fi/whatsmeow/types"
	"go.mau.fi/whatsmeow/types/events"
	waLog "go.mau.fi/whatsmeow/util/log"

	"github.com/skip2/go-qrcode"
)

// GetOrCreateDeviceForTenant retorna o device correto para o tenant.
//
// Regra de isolamento multi-tenant:
//   - Se existe linha em tenant_device para o tenantID: carrega o device pelo
//     JID correspondente. Se o device sumiu da tabela whatsmeow_device (foi
//     deslogado), trata como "nao pareado" e devolve um NewDevice (gera QR).
//   - Se NAO existe linha: devolve um device novo, ainda sem JID. O JID sera
//     gravado em tenant_device quando o evento PairSuccess chegar.
//
// IMPORTANTE: nunca mais usar container.GetAllDevices()[0] — isso vazava o
// mesmo device entre todos os tenants.
func GetOrCreateDeviceForTenant(ctx context.Context, db *sql.DB, container *sqlstore.Container, tenantID string) (*store.Device, error) {
	var jidStr string
	err := db.QueryRowContext(ctx,
		"SELECT jid FROM tenant_device WHERE tenant_id = $1",
		tenantID,
	).Scan(&jidStr)

	if err == sql.ErrNoRows {
		return container.NewDevice(), nil
	}
	if err != nil {
		return nil, fmt.Errorf("erro lendo tenant_device: %w", err)
	}

	jid, err := types.ParseJID(jidStr)
	if err != nil {
		return nil, fmt.Errorf("JID invalido em tenant_device(%s): %w", tenantID, err)
	}

	device, err := container.GetDevice(ctx, jid)
	if err != nil {
		return nil, fmt.Errorf("erro carregando device %s: %w", jid, err)
	}
	if device == nil {
		// Device foi deslogado (whatsmeow_device sumiu) mas tenant_device
		// ainda aponta para ele. Limpa o mapeamento orfao e devolve novo
		// device para o tenant parear de novo.
		log.Printf("[%s] device %s orfao em tenant_device — limpando e gerando QR novo", tenantID, jid)
		_, _ = db.ExecContext(ctx, "DELETE FROM tenant_device WHERE tenant_id = $1", tenantID)
		return container.NewDevice(), nil
	}
	return device, nil
}

// rememberPairing grava (ou atualiza) o JID pareado para o tenant.
// E chamado a partir do handler do evento PairSuccess.
//
// Protecao contra hijack: se outro tenant ja possui esse JID, recusamos a
// gravacao (retorna erro). O caller deve deslogar o cliente para evitar que
// dois tenants compartilhem o mesmo numero WhatsApp.
func rememberPairing(ctx context.Context, db *sql.DB, tenantID string, jid types.JID) error {
	jidStr := jid.String()

	var ownerTenant string
	err := db.QueryRowContext(ctx,
		"SELECT tenant_id FROM tenant_device WHERE jid = $1",
		jidStr,
	).Scan(&ownerTenant)

	if err == nil && ownerTenant != tenantID {
		return fmt.Errorf("JID %s ja pertence ao tenant %s", jidStr, ownerTenant)
	}
	if err != nil && err != sql.ErrNoRows {
		return fmt.Errorf("erro consultando tenant_device: %w", err)
	}

	_, err = db.ExecContext(ctx, `
		INSERT INTO tenant_device (tenant_id, jid, updated_at)
		VALUES ($1, $2, NOW())
		ON CONFLICT (tenant_id) DO UPDATE
		SET jid = EXCLUDED.jid, updated_at = NOW()
	`, tenantID, jidStr)
	if err != nil {
		return fmt.Errorf("erro gravando tenant_device: %w", err)
	}
	return nil
}

// forgetPairing remove o mapeamento tenant→jid (usado no Logout).
func forgetPairing(ctx context.Context, db *sql.DB, tenantID string) {
	_, err := db.ExecContext(ctx, "DELETE FROM tenant_device WHERE tenant_id = $1", tenantID)
	if err != nil {
		log.Printf("[%s] erro removendo tenant_device: %v", tenantID, err)
	}
}

// SessionStatus representa o estado de uma sessão WhatsApp
type SessionStatus struct {
	TenantID string `json:"tenantId"`
	Status   string `json:"status"`
	QR       string `json:"qr,omitempty"`
}

// Session encapsula uma conexão whatsmeow por tenant
type Session struct {
	TenantID       string
	Client         *whatsmeow.Client
	Status         string
	QR             string
	reconnecting   bool
	reconnectCount int
	mu             sync.Mutex
	stopKeepalive  chan struct{}
}

// SessionManager gerencia sessões de múltiplos tenants
type SessionManager struct {
	db          *sql.DB
	dbURL       string
	container   *sqlstore.Container // unico, compartilhado — isolamento e feito por device JID
	sessions    map[string]*Session
	hub         *Hub
	mu          sync.RWMutex
	logLevel    string
	maxSessions int
}

func NewSessionManager(db *sql.DB, hub *Hub) *SessionManager {
	dbURL := os.Getenv("DATABASE_URL")
	m := &SessionManager{
		db:          db,
		dbURL:       dbURL,
		sessions:    make(map[string]*Session),
		hub:         hub,
		maxSessions: 100,
	}

	// Criar container uma vez. As tabelas whatsmeow_* sao compartilhadas, mas
	// cada tenant tem seu proprio device (linha em whatsmeow_device com JID
	// distinto). O mapeamento tenant→jid esta em tenant_device.
	logger := waLog.Stdout("Store", "WARN", true)
	container, err := sqlstore.New(context.Background(), "postgres", dbURL, logger)
	if err != nil {
		log.Fatalf("erro criando sqlstore.Container: %v", err)
	}
	m.container = container
	return m
}

// SessionCount retorna o número de sessões ativas
func (m *SessionManager) SessionCount() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return len(m.sessions)
}

// Connect inicia ou reconecta uma sessão para o tenant
func (m *SessionManager) Connect(tenantID string) (*Session, error) {
	m.mu.Lock()

	// Já conectado?
	if sess, ok := m.sessions[tenantID]; ok {
		m.mu.Unlock()
		sess.mu.Lock()
		if sess.Client != nil && sess.Client.IsConnected() {
			sess.mu.Unlock()
			return sess, nil
		}
		sess.mu.Unlock()
		m.Disconnect(tenantID)
		m.mu.Lock()
	}

	// Limite de sessões simultâneas
	if len(m.sessions) >= m.maxSessions {
		m.mu.Unlock()
		return nil, fmt.Errorf("limite de %d sessões simultâneas atingido", m.maxSessions)
	}

	m.mu.Unlock()

	logLvl := m.logLevel
	if logLvl == "" {
		logLvl = "WARN"
	}

	device, err := GetOrCreateDeviceForTenant(context.Background(), m.db, m.container, tenantID)
	if err != nil {
		return nil, fmt.Errorf("erro ao obter device do tenant: %w", err)
	}

	clientLog := waLog.Stdout("Client/"+tenantID, logLvl, true)
	client := whatsmeow.NewClient(device, clientLog)

	sess := &Session{
		TenantID: tenantID,
		Client:   client,
		Status:   "connecting",
	}

	// Segurança e performance
	client.EnableAutoReconnect = true
	client.EmitAppStateEventsOnFullSync = false

	// Registrar event handler
	client.AddEventHandler(func(evt interface{}) {
		m.handleEvent(sess, evt)
	})

	// Conectar
	if client.Store.ID == nil {
		// Novo dispositivo — precisa de QR
		qrChan, _ := client.GetQRChannel(context.Background())
		err = client.Connect()
		if err != nil {
			return nil, fmt.Errorf("erro ao conectar: %w", err)
		}

		go m.processQRChannel(sess, qrChan)
	} else {
		// Device existente — reconectar direto
		err = client.Connect()
		if err != nil {
			return nil, fmt.Errorf("erro ao reconectar: %w", err)
		}
		log.Printf("[%s] 🔄 Reconectando com sessão existente (JID=%s)...", tenantID, client.Store.ID)
	}

	m.mu.Lock()
	m.sessions[tenantID] = sess
	m.mu.Unlock()

	// Iniciar keepalive robusto (mantem sessão viva contra queda por ociosidade)
	sess.stopKeepalive = make(chan struct{})
	go m.keepaliveLoop(sess)

	return sess, nil
}

// keepaliveLoop envia presença periodicamente para manter sessão WhatsApp ativa.
// Previne desconexão por ociosidade (timeout de inatividade do servidor WhatsApp).
func (m *SessionManager) keepaliveLoop(sess *Session) {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-sess.stopKeepalive:
			return
		case <-ticker.C:
			sess.mu.Lock()
			client := sess.Client
			status := sess.Status
			sess.mu.Unlock()
			if client != nil && client.IsConnected() && status == "connected" {
				if err := client.SendPresence(context.Background(), types.PresenceAvailable); err != nil {
					log.Printf("[%s] ⚠️  keepalive erro: %v", sess.TenantID, err)
				} else {
					log.Printf("[%s] 💚 keepalive OK", sess.TenantID)
				}
			}
		}
	}
}

// processQRChannel lida com o fluxo de QR code
func (m *SessionManager) processQRChannel(sess *Session, qrChan <-chan whatsmeow.QRChannelItem) {
	for evt := range qrChan {
		switch evt.Event {
		case "code":
			qrPNG, err := qrcode.Encode(evt.Code, qrcode.Medium, 256)
			if err != nil {
				log.Printf("[%s] Erro ao gerar QR: %v", sess.TenantID, err)
				continue
			}
			qrBase64 := "data:image/png;base64," + base64.StdEncoding.EncodeToString(qrPNG)

			sess.mu.Lock()
			sess.Status = "qr"
			sess.QR = qrBase64
			sess.mu.Unlock()

			m.hub.Broadcast(Event{
				Type: "connection.update",
				Data: map[string]interface{}{
					"tenantId": sess.TenantID,
					"status":   "qr",
					"qr":       qrBase64,
				},
			})
			log.Printf("[%s] 📱 QR code gerado", sess.TenantID)

		case "login":
			sess.mu.Lock()
			sess.Status = "connected"
			sess.QR = ""
			sess.mu.Unlock()

			m.hub.Broadcast(Event{
				Type: "connection.update",
				Data: map[string]interface{}{
					"tenantId": sess.TenantID,
					"status":   "connected",
				},
			})
			log.Printf("[%s] ✅ Conectado via QR", sess.TenantID)

		case "timeout":
			sess.mu.Lock()
			sess.Status = "disconnected"
			sess.QR = ""
			sess.mu.Unlock()

			m.hub.Broadcast(Event{
				Type: "connection.update",
				Data: map[string]interface{}{
					"tenantId": sess.TenantID,
					"status":   "timeout",
				},
			})
			log.Printf("[%s] ⏰ QR timeout", sess.TenantID)
		}
	}
}

// Disconnect desconecta sem apagar credenciais
func (m *SessionManager) Disconnect(tenantID string) {
	m.mu.Lock()
	sess, ok := m.sessions[tenantID]
	if ok {
		delete(m.sessions, tenantID)
	}
	m.mu.Unlock()

	if ok && sess.Client != nil {
		sess.Client.Disconnect()
	}

	m.hub.Broadcast(Event{
		Type: "connection.update",
		Data: map[string]interface{}{
			"tenantId": tenantID,
			"status":   "disconnected",
		},
	})
}

// Logout desconecta E apaga credenciais
func (m *SessionManager) Logout(tenantID string) error {
	m.mu.Lock()
	sess, ok := m.sessions[tenantID]
	if ok {
		delete(m.sessions, tenantID)
	}
	m.mu.Unlock()

	// Sempre limpa o mapeamento tenant→jid, mesmo se a sessao em memoria sumiu.
	forgetPairing(context.Background(), m.db, tenantID)

	if ok && sess.Client != nil {
		err := sess.Client.Logout(context.Background())
		sess.Client.Disconnect()
		return err
	}

	return nil
}

// GetSession retorna a sessão de um tenant
func (m *SessionManager) GetSession(tenantID string) *Session {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.sessions[tenantID]
}

// GetAllStatuses retorna o status de todas sessões
func (m *SessionManager) GetAllStatuses() []SessionStatus {
	m.mu.RLock()
	defer m.mu.RUnlock()

	statuses := make([]SessionStatus, 0, len(m.sessions))
	for _, sess := range m.sessions {
		sess.mu.Lock()
		statuses = append(statuses, SessionStatus{
			TenantID: sess.TenantID,
			Status:   sess.Status,
			QR:       sess.QR,
		})
		sess.mu.Unlock()
	}
	return statuses
}

// DisconnectAll desconecta todas as sessões (shutdown)
func (m *SessionManager) DisconnectAll() {
	m.mu.Lock()
	tenants := make([]string, 0, len(m.sessions))
	for id := range m.sessions {
		tenants = append(tenants, id)
	}
	m.mu.Unlock()

	for _, id := range tenants {
		m.Disconnect(id)
	}
}

// handleEvent processa eventos do whatsmeow e retransmite via WebSocket
func (m *SessionManager) handleEvent(sess *Session, evt interface{}) {
	switch v := evt.(type) {
	case *events.HistorySync:
		// Ignorar completamente — não processamos mensagens antigas
		return

	case *events.Message:
		m.handleMessage(sess, v)

	case *events.PairSuccess:
		// QR foi escaneado pelo telefone — gravar mapeamento tenant→jid AGORA.
		// Antes do Connected chegar, garantimos que este JID nao pode ser
		// reutilizado por outro tenant.
		err := rememberPairing(context.Background(), m.db, sess.TenantID, v.ID)
		if err != nil {
			log.Printf("[%s] ❌ Recusando pareamento: %v", sess.TenantID, err)
			// JID ja pertence a outro tenant — deslogar imediatamente.
			go func() {
				_ = sess.Client.Logout(context.Background())
				sess.Client.Disconnect()
				m.hub.Broadcast(Event{
					Type: "connection.update",
					Data: map[string]interface{}{
						"tenantId": sess.TenantID,
						"status":   "rejected",
						"error":    "Este numero WhatsApp ja esta vinculado a outro usuario.",
					},
				})
			}()
			return
		}
		log.Printf("[%s] 🔐 Pareamento registrado: %s", sess.TenantID, v.ID)

	case *events.Connected:
		// FIX: events.Connected dispara quando o cliente conecta no servidor WhatsApp,
		// nao necessariamente quando um device esta pareado. Sem device pareado
		// (Store.ID == nil), a sessao ainda esta em handshake/QR pending — nao deve
		// reportar 'connected' para o frontend, senao a UI mente para o usuario.
		paired := sess.Client != nil && sess.Client.Store != nil && sess.Client.Store.ID != nil
		sess.mu.Lock()
		if paired {
			sess.Status = "connected"
			sess.QR = ""
			sess.reconnecting = false
			sess.reconnectCount = 0
		} else {
			sess.Status = "pairing"
		}
		statusEvt := sess.Status
		sess.mu.Unlock()
		m.hub.Broadcast(Event{
			Type: "connection.update",
			Data: map[string]interface{}{
				"tenantId": sess.TenantID,
				"status":   statusEvt,
			},
		})
		if paired {
			log.Printf("[%s] ✅ Conectado e pareado (evento Connected, JID=%s)", sess.TenantID, sess.Client.Store.ID)
		} else {
			log.Printf("[%s] handshake (Connected sem device pareado — aguardando QR)", sess.TenantID)
		}

	case *events.Disconnected:
		sess.mu.Lock()
		sess.reconnectCount++
		sess.Status = "reconnecting"
		wasReconnecting := sess.reconnecting
		sess.reconnecting = true
		client := sess.Client
		sess.mu.Unlock()

		m.hub.Broadcast(Event{
			Type: "connection.update",
			Data: map[string]interface{}{
				"tenantId": sess.TenantID,
				"status":   "reconnecting",
			},
		})
		log.Printf("[%s] ⚠️  Desconectado (tentativa %d) — reconectando...", sess.TenantID, sess.reconnectCount)

		// Forçar reconexão agressiva com backoff
		go func() {
			delay := time.Duration(sess.reconnectCount) * 2 * time.Second
			if delay > 30*time.Second {
				delay = 30 * time.Second
			}
			time.Sleep(delay)
			if client != nil {
				if err := client.Connect(); err != nil {
					log.Printf("[%s] ❌ falha ao reconectar: %v", sess.TenantID, err)
				} else {
					log.Printf("[%s] ✅ reconectado com sucesso", sess.TenantID)
					if wasReconnecting {
						// Reset counter on successful reconnect
						sess.mu.Lock()
						sess.reconnectCount = 0
						sess.reconnecting = false
						sess.mu.Unlock()
					}
				}
			}
		}()

	case *events.LoggedOut:
		// Servidor invalidou a sessao (logout remoto, banido, conflito de device).
		// Limpa o mapeamento tenant→jid para evitar "device orfao" no proximo connect.
		forgetPairing(context.Background(), m.db, sess.TenantID)
		sess.mu.Lock()
		sess.Status = "disconnected"
		sess.QR = ""
		sess.mu.Unlock()
		m.hub.Broadcast(Event{
			Type: "connection.update",
			Data: map[string]interface{}{
				"tenantId": sess.TenantID,
				"status":   "logged_out",
			},
		})
		log.Printf("[%s] 🚪 LoggedOut — mapeamento removido", sess.TenantID)

	case *events.Presence:
		available := "available"
		if v.Unavailable {
			available = "unavailable"
		}
		m.hub.Broadcast(Event{
			Type: "presence.update",
			Data: map[string]interface{}{
				"tenantId": sess.TenantID,
				"jid":      v.From.String(),
				"presence": available,
			},
		})

	case *events.PushName:
		m.hub.Broadcast(Event{
			Type: "contacts.upsert",
			Data: map[string]interface{}{
				"tenantId": sess.TenantID,
				"contacts": []map[string]string{
					{"jid": v.JID.String(), "name": v.NewPushName},
				},
			},
		})
	}
}

// handleMessage converte a mensagem whatsmeow para o formato Baileys esperado pelo Node.js
func (m *SessionManager) handleMessage(sess *Session, msg *events.Message) {
	// Ignorar mensagens antigas (history sync) — só processar mensagens dos últimos 60s
	if time.Since(msg.Info.Timestamp) > 60*time.Second {
		return
	}

	text := ""
	msgType := "text"

	if msg.Message.GetConversation() != "" {
		text = msg.Message.GetConversation()
	} else if msg.Message.GetExtendedTextMessage() != nil {
		text = msg.Message.GetExtendedTextMessage().GetText()
	} else if msg.Message.GetImageMessage() != nil {
		msgType = "image"
		text = msg.Message.GetImageMessage().GetCaption()
	} else if msg.Message.GetVideoMessage() != nil {
		msgType = "video"
		text = msg.Message.GetVideoMessage().GetCaption()
	} else if msg.Message.GetAudioMessage() != nil {
		msgType = "audio"
	} else if msg.Message.GetDocumentMessage() != nil {
		msgType = "document"
		text = msg.Message.GetDocumentMessage().GetCaption()
	} else if msg.Message.GetLocationMessage() != nil {
		msgType = "location"
	} else if msg.Message.GetContactMessage() != nil {
		msgType = "contact"
	} else if msg.Message.GetStickerMessage() != nil {
		msgType = "sticker"
	}

	// Formato compatível com Baileys
	messageData := map[string]interface{}{
		"key": map[string]interface{}{
			"remoteJid": msg.Info.Chat.String(),
			"fromMe":    msg.Info.IsFromMe,
			"id":        msg.Info.ID,
		},
		"messageTimestamp": msg.Info.Timestamp.Unix(),
		"pushName":         msg.Info.PushName,
		"message":          map[string]interface{}{},
	}

	switch msgType {
	case "text":
		messageData["message"] = map[string]interface{}{
			"conversation": text,
		}
	case "image":
		messageData["message"] = map[string]interface{}{
			"imageMessage": map[string]interface{}{
				"caption":  text,
				"mimetype": msg.Message.GetImageMessage().GetMimetype(),
			},
		}
	case "audio":
		ptt := false
		if msg.Message.GetAudioMessage() != nil {
			ptt = msg.Message.GetAudioMessage().GetPTT()
		}
		messageData["message"] = map[string]interface{}{
			"audioMessage": map[string]interface{}{
				"ptt":      ptt,
				"mimetype": msg.Message.GetAudioMessage().GetMimetype(),
			},
		}
	case "video":
		messageData["message"] = map[string]interface{}{
			"videoMessage": map[string]interface{}{
				"caption":  text,
				"mimetype": msg.Message.GetVideoMessage().GetMimetype(),
			},
		}
	case "document":
		messageData["message"] = map[string]interface{}{
			"documentMessage": map[string]interface{}{
				"caption":  text,
				"mimetype": msg.Message.GetDocumentMessage().GetMimetype(),
				"fileName": msg.Message.GetDocumentMessage().GetFileName(),
			},
		}
	case "location":
		loc := msg.Message.GetLocationMessage()
		messageData["message"] = map[string]interface{}{
			"locationMessage": map[string]interface{}{
				"degreesLatitude":  loc.GetDegreesLatitude(),
				"degreesLongitude": loc.GetDegreesLongitude(),
			},
		}
	case "contact":
		messageData["message"] = map[string]interface{}{
			"contactMessage": map[string]interface{}{
				"displayName": msg.Message.GetContactMessage().GetDisplayName(),
				"vcard":       msg.Message.GetContactMessage().GetVcard(),
			},
		}
	case "sticker":
		messageData["message"] = map[string]interface{}{
			"stickerMessage": map[string]interface{}{
				"mimetype": msg.Message.GetStickerMessage().GetMimetype(),
			},
		}
	}

	m.hub.Broadcast(Event{
		Type: "message",
		Data: map[string]interface{}{
			"tenantId": sess.TenantID,
			"message":  messageData,
		},
	})
}
