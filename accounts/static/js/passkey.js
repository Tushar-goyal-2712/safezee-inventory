"use strict";

/* ============================================================
   SAFEZEE Inventory — passkey (WebAuthn) client logic.
   No external libraries. Talks to accounts/views.py.
   ============================================================ */

(function () {
    function getCookie(name) {
        const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
        return match ? decodeURIComponent(match[2]) : null;
    }
    const CSRF_TOKEN = getCookie("csrftoken");

    /* ---------- base64url <-> ArrayBuffer ---------- */
    function b64urlToBuffer(b64url) {
        const padded = b64url.replace(/-/g, "+").replace(/_/g, "/");
        const padding = "=".repeat((4 - (padded.length % 4)) % 4);
        const binary = atob(padded + padding);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        return bytes.buffer;
    }

    function bufferToB64url(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = "";
        for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
        return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
    }

    /* ---------- Convert server options JSON -> browser-ready options ---------- */
    function prepareCreationOptions(options) {
        options.challenge = b64urlToBuffer(options.challenge);
        options.user.id = b64urlToBuffer(options.user.id);
        if (options.excludeCredentials) {
            options.excludeCredentials = options.excludeCredentials.map((c) => ({
                ...c,
                id: b64urlToBuffer(c.id),
            }));
        }
        return options;
    }

    function prepareRequestOptions(options) {
        options.challenge = b64urlToBuffer(options.challenge);
        if (options.allowCredentials) {
            options.allowCredentials = options.allowCredentials.map((c) => ({
                ...c,
                id: b64urlToBuffer(c.id),
            }));
        }
        return options;
    }

    /* ---------- Convert browser credential -> JSON for the server ---------- */
    function registrationCredentialToJSON(credential) {
        const response = credential.response;
        return {
            id: credential.id,
            rawId: bufferToB64url(credential.rawId),
            type: credential.type,
            clientExtensionResults: credential.getClientExtensionResults
                ? credential.getClientExtensionResults()
                : {},
            response: {
                clientDataJSON: bufferToB64url(response.clientDataJSON),
                attestationObject: bufferToB64url(response.attestationObject),
                transports: response.getTransports ? response.getTransports() : [],
            },
        };
    }

    function authenticationCredentialToJSON(credential) {
        const response = credential.response;
        return {
            id: credential.id,
            rawId: bufferToB64url(credential.rawId),
            type: credential.type,
            clientExtensionResults: credential.getClientExtensionResults
                ? credential.getClientExtensionResults()
                : {},
            response: {
                clientDataJSON: bufferToB64url(response.clientDataJSON),
                authenticatorData: bufferToB64url(response.authenticatorData),
                signature: bufferToB64url(response.signature),
                userHandle: response.userHandle ? bufferToB64url(response.userHandle) : null,
            },
        };
    }

    function isSupported() {
        return !!(window.PublicKeyCredential && navigator.credentials);
    }

    function setLoading(button, loading) {
        if (!button) return;
        button.disabled = loading;
        const label = button.querySelector(".btn-label");
        const spinner = button.querySelector(".spinner-border");
        if (label) label.classList.toggle("d-none", loading);
        if (spinner) spinner.classList.toggle("d-none", !loading);
    }

    function showError(elId, message) {
        const el = document.getElementById(elId);
        if (!el) return;
        el.textContent = message;
        el.classList.remove("d-none");
    }

    /* ============================================================
       REGISTER — enroll a new passkey (requires the shared secret)
       ============================================================ */
    async function register(secret, deviceLabel) {
        const submitBtn = document.querySelector("#registerForm button[type=submit]");
        document.getElementById("registerError").classList.add("d-none");

        if (!isSupported()) {
            document.getElementById("registerUnsupported").classList.remove("d-none");
            return;
        }

        setLoading(submitBtn, true);
        try {
            const optionsRes = await fetch(window.SZ_AUTH_URLS.registerOptions, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF_TOKEN },
                body: JSON.stringify({ secret }),
            });
            if (!optionsRes.ok) {
                throw new Error(
                    optionsRes.status === 403
                        ? "Incorrect enrollment secret."
                        : "Could not start registration."
                );
            }
            const options = prepareCreationOptions(await optionsRes.json());

            const credential = await navigator.credentials.create({ publicKey: options });
            const credentialJSON = registrationCredentialToJSON(credential);

            const verifyRes = await fetch(window.SZ_AUTH_URLS.registerVerify, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF_TOKEN },
                body: JSON.stringify({
                    secret,
                    device_label: deviceLabel,
                    credential: credentialJSON,
                }),
            });
            const data = await verifyRes.json();
            if (!verifyRes.ok || !data.ok) {
                throw new Error(data.message || "Registration failed.");
            }

            window.location.href = data.redirect || "/";
        } catch (err) {
            console.error(err);

            showError(
                "registerError",
                `${err.name}: ${err.message}`
            );
        } finally {
            setLoading(submitBtn, false);
        }
    }

    /* ============================================================
       LOGIN — sign in with an already-registered passkey
       ============================================================ */
    async function login() {
        const loginBtn = document.getElementById("loginBtn");
        document.getElementById("loginError").classList.add("d-none");

        if (!isSupported()) {
            document.getElementById("loginUnsupported").classList.remove("d-none");
            return;
        }

        setLoading(loginBtn, true);
        try {
            const optionsRes = await fetch(window.SZ_AUTH_URLS.loginOptions, {
                method: "POST",
                headers: { "X-CSRFToken": CSRF_TOKEN },
            });
            const optionsData = await optionsRes.json();
            if (!optionsRes.ok || optionsData.ok === false) {
                throw new Error(optionsData.message || "Could not start sign-in.");
            }
            const options = prepareRequestOptions(optionsData);

            const credential = await navigator.credentials.get({ publicKey: options });
            const credentialJSON = authenticationCredentialToJSON(credential);

            const verifyRes = await fetch(window.SZ_AUTH_URLS.loginVerify, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF_TOKEN },
                body: JSON.stringify({ credential: credentialJSON }),
            });
            const data = await verifyRes.json();
            if (!verifyRes.ok || !data.ok) {
                throw new Error(data.message || "Sign-in failed.");
            }

            const params = new URLSearchParams(window.location.search);
            window.location.href = params.get("next") || data.redirect || "/";
        } catch (err) {
            const message =
                err.name === "NotAllowedError"
                    ? "Sign-in was cancelled or timed out."
                    : err.message || "Sign-in failed.";
            showError("loginError", message);
        } finally {
            setLoading(loginBtn, false);
        }
    }

    window.SZPasskey = { register, login };
})();
