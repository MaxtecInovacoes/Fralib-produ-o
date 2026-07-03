// whatsmeow_/handlers.go
// HTTP e WebSocket handlers para o bridge Go do FraLib.
// Implementacao minima - retornar dados basicos. Integracao completa fica
// para versao futura quando o main.go estiver rodando em prod.

package main

import (
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/gorilla/websocket"
)

// handleSessions retorna JSON com status de todas as sessoes ativas.
// GET /api/sessions
func handleSessions(sm *SessionManager) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch r.Method {
		case http.MethodGet:
			statuses := sm.GetAllStatuses()
			if err := json.NewEncoder(w).Encode(statuses); err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
			}

		case http.MethodPost:
			// POST /api/sessions {tenant_id: "..."}
			var body struct {
				TenantID string `json:"tenant_id"`
			}
			if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
				http.Error(w, "JSON invalido", http.StatusBadRequest)
				return
			}
			if body.TenantID == "" {
				http.Error(w, "tenant_id obrigatorio", http.StatusBadRequest)
				return
			}
			sess, err := sm.Connect(body.TenantID)
			if err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
			w.WriteHeader(http.StatusCreated)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"tenant_id": sess.TenantID,
				"status":    "connecting",
			})

		default:
			http.Error(w, "metodo nao suportado", http.StatusMethodNotAllowed)
		}
	}
}

// upgrader para WebSocket
var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		// TODO: restringir origem em prod
		return true
	},
}

// handleWebSocket faz upgrade da conexao para WebSocket e streama eventos.
// GET /ws
func handleWebSocket(sm *SessionManager, hub *Hub) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			fmt.Printf("upgrade WS falhou: %v\n", err)
			return
		}
		defer conn.Close()

		// Subscribe aos eventos do hub
		ch, unsubscribe := hub.Subscribe()
		defer unsubscribe()

		// Loop: envia eventos do hub para o cliente WS
		for evt := range ch {
			if err := conn.WriteJSON(evt); err != nil {
				return
			}
		}
	}
}