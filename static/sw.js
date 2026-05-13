// Service Worker for Push Notifications - Alma do Livro

const CACHE_NAME = 'alma-do-livro-v1';

// Install event
self.addEventListener('install', (event) => {
    console.log('[SW] Service Worker installed');
    self.skipWaiting();
});

// Activate event
self.addEventListener('activate', (event) => {
    console.log('[SW] Service Worker activated');
    event.waitUntil(clients.claim());
});

// Push event - receive push notifications
self.addEventListener('push', (event) => {
    console.log('[SW] Push received:', event);
    
    let data = {
        title: 'Alma do Livro',
        body: 'Tens uma nova notificação!',
        icon: '/static/icon-192.png',
        badge: '/static/badge-72.png',
        tag: 'alma-notification',
        data: { url: '/' }
    };
    
    if (event.data) {
        try {
            data = { ...data, ...event.data.json() };
        } catch (e) {
            data.body = event.data.text();
        }
    }
    
    const options = {
        body: data.body,
        icon: data.icon || '/static/icon-192.png',
        badge: data.badge || '/static/badge-72.png',
        tag: data.tag || 'alma-notification',
        data: data.data || { url: '/' },
        vibrate: [100, 50, 100],
        actions: data.actions || [
            { action: 'open', title: 'Abrir' },
            { action: 'close', title: 'Fechar' }
        ],
        requireInteraction: data.requireInteraction || false
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification clicked:', event);
    
    event.notification.close();
    
    if (event.action === 'close') {
        return;
    }
    
    const urlToOpen = event.notification.data?.url || '/explorer';
    
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // Check if there's already a window open
                for (const client of clientList) {
                    if (client.url.includes(self.location.origin) && 'focus' in client) {
                        client.navigate(urlToOpen);
                        return client.focus();
                    }
                }
                // Open new window if none exists
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

// Background sync for offline actions
self.addEventListener('sync', (event) => {
    console.log('[SW] Background sync:', event.tag);
});
