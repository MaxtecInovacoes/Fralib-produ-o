window.TwoFactorAuth = {
    checkStatus: async function() {
        console.log("[2FA] Dummy status check (checkStatus)");
        return { ativo: false };
    },
    verificarStatus: async function() {
        return { ativo: false };
    },
    setup: function() {
        console.log("[2FA] Dummy setup called");
    }
};
