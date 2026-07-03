// whatsmeow_/hub.go
// Hub simples para broadcast de eventos do whatsmeow para clientes WebSocket.
// Mantido minimo - o SessionManager original (em session.go) faz a maior parte.

package main

import (
	"sync"

	waLog "go.mau.fi/whatsmeow/util/log"
)

// Hub distribui eventos para subscribers WebSocket.
// Implementacao minima - suficiente para o main.go compilar e o /ws funcionar.
// Para alta concorrencia, substituir por implementacao com channels buffered.
type Hub struct {
	mu          sync.RWMutex
	subscribers map[chan<- Event]struct{}
	logger      waLog.Logger
}

// Event representa uma mensagem WhatsApp (recebida ou enviada).
type Event struct {
	Type string                 `json:"type"`
	Data map[string]interface{} `json:"data"`
}

func newHub(logger waLog.Logger) *Hub {
	return &Hub{
		subscribers: make(map[chan<- Event]struct{}),
		logger:      logger,
	}
}

// Subscribe registra um canal para receber eventos.
// Retorna canal e funcao de unsubscribe.
func (h *Hub) Subscribe() (chan Event, func()) {
	ch := make(chan Event, 32)
	h.mu.Lock()
	h.subscribers[ch] = struct{}{}
	h.mu.Unlock()

	unsubscribe := func() {
		h.mu.Lock()
		if _, ok := h.subscribers[ch]; ok {
			delete(h.subscribers, ch)
			close(ch)
		}
		h.mu.Unlock()
	}
	return ch, unsubscribe
}

// Broadcast envia evento para todos os subscribers.
// Se algum subscriber tiver buffer cheio, descartamos (nao bloqueamos).
func (h *Hub) Broadcast(evt Event) {
	h.mu.RLock()
	defer h.mu.RUnlock()
	for ch := range h.subscribers {
		select {
		case ch <- evt:
		default:
			// subscriber lento - drop
			h.logger.Warnf("subscriber lento, descartando evento tipo=%s", evt.Type)
		}
	}
}

// SubscriberCount retorna numero de subscribers ativos.
func (h *Hub) SubscriberCount() int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return len(h.subscribers)
}