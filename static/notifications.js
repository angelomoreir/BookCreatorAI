// Push Notifications System - Alma do Livro

const NotificationSystem = {
    vapidPublicKey: null,
    swRegistration: null,
    isSupported: false,
    
    // Initialize the notification system
    async init() {
        // Check if notifications are supported
        if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) {
            console.log('[Notifications] Push notifications not supported');
            this.isSupported = false;
            return false;
        }
        
        this.isSupported = true;
        
        try {
            // Register service worker
            this.swRegistration = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
            console.log('[Notifications] Service Worker registered');
            
            // Get VAPID public key from server
            const response = await fetch('/api/notifications/vapid-key');
            const data = await response.json();
            if (data.success) {
                this.vapidPublicKey = data.publicKey;
            }
            
            // Update UI based on current permission
            this.updateUI();
            
            return true;
        } catch (error) {
            console.error('[Notifications] Init error:', error);
            return false;
        }
    },
    
    // Check current permission status
    getPermissionStatus() {
        if (!this.isSupported) return 'unsupported';
        return Notification.permission; // 'granted', 'denied', 'default'
    },
    
    // Request permission and subscribe
    async requestPermission() {
        if (!this.isSupported) {
            this.showToast('O teu browser não suporta notificações push', 'error');
            return false;
        }
        
        try {
            const permission = await Notification.requestPermission();
            
            if (permission === 'granted') {
                await this.subscribe();
                this.showToast('Notificações ativadas com sucesso!', 'success');
                this.updateUI();
                return true;
            } else if (permission === 'denied') {
                this.showToast('Permissão de notificações negada', 'error');
                return false;
            }
            
            return false;
        } catch (error) {
            console.error('[Notifications] Permission error:', error);
            this.showToast('Erro ao ativar notificações', 'error');
            return false;
        }
    },
    
    // Subscribe to push notifications
    async subscribe() {
        if (!this.swRegistration || !this.vapidPublicKey) {
            console.error('[Notifications] Missing SW registration or VAPID key');
            return null;
        }
        
        try {
            // Convert VAPID key to Uint8Array
            const applicationServerKey = this.urlBase64ToUint8Array(this.vapidPublicKey);
            
            // Subscribe to push
            const subscription = await this.swRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: applicationServerKey
            });
            
            // Send subscription to server
            await this.saveSubscription(subscription);
            
            console.log('[Notifications] Subscribed successfully');
            return subscription;
        } catch (error) {
            console.error('[Notifications] Subscribe error:', error);
            return null;
        }
    },
    
    // Save subscription to server
    async saveSubscription(subscription) {
        try {
            const response = await fetch('/api/notifications/subscribe', {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    subscription: subscription.toJSON()
                })
            });
            
            const data = await response.json();
            return data.success;
        } catch (error) {
            console.error('[Notifications] Save subscription error:', error);
            return false;
        }
    },
    
    // Unsubscribe from push notifications
    async unsubscribe() {
        try {
            const subscription = await this.swRegistration.pushManager.getSubscription();
            
            if (subscription) {
                // Unsubscribe from push
                await subscription.unsubscribe();
                
                // Remove from server
                await fetch('/api/notifications/unsubscribe', {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        endpoint: subscription.endpoint
                    })
                });
                
                this.showToast('Notificações desativadas', 'info');
                this.updateUI();
                return true;
            }
            
            return false;
        } catch (error) {
            console.error('[Notifications] Unsubscribe error:', error);
            return false;
        }
    },
    
    // Check if currently subscribed
    async isSubscribed() {
        if (!this.swRegistration) return false;
        
        try {
            const subscription = await this.swRegistration.pushManager.getSubscription();
            return subscription !== null;
        } catch (error) {
            return false;
        }
    },
    
    // Update notification preferences
    async updatePreferences(preferences) {
        try {
            const response = await fetch('/api/notifications/preferences', {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(preferences)
            });
            
            const data = await response.json();
            if (data.success) {
                this.showToast('Preferências atualizadas!', 'success');
            }
            return data.success;
        } catch (error) {
            console.error('[Notifications] Update preferences error:', error);
            return false;
        }
    },
    
    // Update UI elements
    async updateUI() {
        const toggleBtn = document.getElementById('notificationToggle');
        const statusText = document.getElementById('notificationStatus');
        const settingsPanel = document.getElementById('notificationSettings');
        
        if (!this.isSupported) {
            if (toggleBtn) toggleBtn.disabled = true;
            if (statusText) statusText.textContent = 'Não suportado';
            return;
        }
        
        const permission = this.getPermissionStatus();
        const subscribed = await this.isSubscribed();
        
        if (toggleBtn) {
            toggleBtn.checked = subscribed;
            toggleBtn.disabled = permission === 'denied';
        }
        
        if (statusText) {
            if (permission === 'denied') {
                statusText.textContent = 'Bloqueadas pelo browser';
                statusText.className = 'text-red-400 text-sm';
            } else if (subscribed) {
                statusText.textContent = 'Ativadas';
                statusText.className = 'text-green-400 text-sm';
            } else {
                statusText.textContent = 'Desativadas';
                statusText.className = 'text-gray-400 text-sm';
            }
        }
        
        if (settingsPanel) {
            settingsPanel.style.display = subscribed ? 'block' : 'none';
        }
    },
    
    // Show local notification (for testing)
    showLocalNotification(title, body, options = {}) {
        if (this.getPermissionStatus() !== 'granted') {
            console.log('[Notifications] Permission not granted');
            return;
        }
        
        const defaultOptions = {
            body: body,
            icon: '/static/icon-192.png',
            badge: '/static/badge-72.png',
            tag: 'local-notification',
            ...options
        };
        
        new Notification(title, defaultOptions);
    },
    
    // Show toast message
    showToast(message, type = 'info') {
        // Use existing toast system if available
        if (typeof showToast === 'function') {
            showToast(message, type);
            return;
        }
        
        // Fallback toast
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-lg text-white z-50 transition-all transform ${
            type === 'success' ? 'bg-green-600' : 
            type === 'error' ? 'bg-red-600' : 
            'bg-purple-600'
        }`;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },
    
    // Helper: Convert base64 to Uint8Array
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');
        
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        
        return outputArray;
    }
};

// Toggle notifications
async function toggleNotifications() {
    const subscribed = await NotificationSystem.isSubscribed();
    
    if (subscribed) {
        await NotificationSystem.unsubscribe();
    } else {
        await NotificationSystem.requestPermission();
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    NotificationSystem.init();
});
