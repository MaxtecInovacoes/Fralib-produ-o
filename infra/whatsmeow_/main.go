// whatsmeow_/main.go
// Entry point do bridge Go do FraLib - serve HTTP+WebSocket na porta 3001
// Compila com: go build -o meowhats .
//
// Instalacao:
//   sudo cp meowhats /usr/local/bin/meowhats
//   sudo cp infra/systemd/fralib-meowhats.service /etc/systemd/system/
//   sudo systemctl enable --now fralib-meowhats
//
// Variaveis de ambiente (carregadas de /etc/fralib/fralib.env):
//   MEOWHATS_PORT      - porta HTTP (default 3001)
//   MEOWHATS_DB_URL    - postgres URL para whatsmeow (ex: postgres://user:pass@localhost:5432/fralib_whatsmeow)
//   MEOWHATS_LOG_LEVEL - log level (DEBUG, INFO, WARN, ERROR)

package main

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	_ "github.com/lib/pq"
	"go.mau.fi/whatsmeow/store/sqlstore"
	waLog "go.mau.fi/whatsmeow/util/log"
)

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	port := getenv("MEOWHATS_PORT", "3001")
	dbURL := getenv("MEOWHATS_DB_URL", "")
	logLevel := getenv("MEOWHATS_LOG_LEVEL", "INFO")

	if dbURL == "" {
		log.Fatal("MEOWHATS_DB_URL nao definida (carregue /etc/fralib/fralib.env)")
	}

	logger := waLog.Stdout("meowhats", logLevel, true)

	// Conectar ao Postgres para o whatsmeow
	db, err := sql.Open("postgres", dbURL)
	if err != nil {
		log.Fatalf("falha abrir postgres: %v", err)
	}
	defer db.Close()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Criar container whatsmeow (cria tabelas se nao existem)
	container := sqlstore.NewWithDB(db, "postgres", waLog.Stdout("sqlstore", logLevel, true), nil)
	if err := container.Upgrade(ctx); err != nil {
		log.Fatalf("falha upgrade whatsmeow schema: %v", err)
	}

	// Criar SessionManager (multi-tenant device manager)
	hub := newHub(logger)
	sm := NewSessionManager(db, hub)
	defer sm.DisconnectAll()

	// HTTP handlers (basicos - implementar conforme session.go)
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, `{"status":"ok","sessions":%d,"uptime_s":%d}`, sm.SessionCount(), uptime())
	})
	mux.HandleFunc("/api/sessions", handleSessions(sm))
	mux.HandleFunc("/ws", handleWebSocket(sm, hub))

	srv := &http.Server{
		Addr:         ":" + port,
		Handler:      mux,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
	}

	// Graceful shutdown
	go func() {
		sig := make(chan os.Signal, 1)
		signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
		<-sig
		log.Println("shutdown solicitado...")
		cancel()
		shutCtx, shutCancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer shutCancel()
		srv.Shutdown(shutCtx)
	}()

	log.Printf("meowhats escutando em :%s (sessions=%d)", port, sm.SessionCount())
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("falha ListenAndServe: %v", err)
	}
	log.Println("meowhats encerrado")
}

var startTime = time.Now()

func uptime() int64 {
	return int64(time.Since(startTime).Seconds())
}