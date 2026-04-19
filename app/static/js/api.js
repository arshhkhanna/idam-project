const API = {
    async login(email, password) {
        const res = await fetch('/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email, password})
        });
        return {status: res.status, data: await res.json()};
    },

    async loginMFA(email, password, mfa_code) {
        const res = await fetch('/auth/login-mfa', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email, password, mfa_code})
        });
        return {status: res.status, data: await res.json()};
    },

    async getProfile(accessToken) {
        const res = await fetch('/users/me', {
            headers: {'Authorization': 'Bearer ' + accessToken}
        });
        return {status: res.status, data: await res.json()};
    },

    async refresh(refreshToken) {
        const res = await fetch('/auth/refresh', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({refresh_token: refreshToken})
        });
        return {status: res.status, data: await res.json()};
    },

    async logout(refreshToken) {
        const res = await fetch('/auth/logout', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({refresh_token: refreshToken})
        });
        return {status: res.status, data: await res.json()};
    },

    async forgotPassword(email) {
        const res = await fetch('/auth/forgot-password', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email})
        });
        return {status: res.status, data: await res.json()};
    },

    async resetPassword(token, new_password) {
        const res = await fetch('/auth/reset-password', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({token, new_password})
        });
        return {status: res.status, data: await res.json()};
    }
};
