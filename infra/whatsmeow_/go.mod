module github.com/fralib/whatsmeow_

go 1.21

require (
	github.com/lib/pq v1.10.9
	github.com/skip2/go-qrcode v0.0.0-20200617195104-da1b6568686e
	go.mau.fi/whatsmeow v0.0.0-20240228165848-89d2f63e9e1d
)

// whatsmeow depende de:
//   - gorilla/websocket (ja vem como transitive)
//   - protobuf
//   - lib/pq (driver postgres)
//
// Para rodar:
//   go mod tidy
//   go build -o meowhats .
//
// Em producao (VPS):
//   cd /opt/whatsmeow_
//   go build -o /usr/local/bin/meowhats .