window.SocketClient = {
    init: async function() {
        console.log("[Socket] Dummy client initialized");
        return true;
    },
    on: function(event, callback) {
        console.log("[Socket] Dummy listener for:", event);
    },
    emit: function(event, data) {
        console.log("[Socket] Dummy emit:", event, data);
    }
};
