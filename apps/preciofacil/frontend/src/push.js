import { api } from "./api.js";

export function pushSupported() {
  return typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window;
}

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)));
}

export async function getExistingSubscription() {
  if (!pushSupported()) return null;
  const registration = await navigator.serviceWorker.ready;
  return registration.pushManager.getSubscription();
}

export async function subscribeToPush(userEmail) {
  if (!pushSupported()) {
    throw new Error("Este navegador no admite notificaciones push.");
  }
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error("Necesitas dar permiso de notificaciones para activar los avisos.");
  }
  const { public_key: publicKey } = await api.vapidPublicKey();
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  });
  const json = subscription.toJSON();
  await api.subscribePush({
    user_email: userEmail,
    endpoint: json.endpoint,
    keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
  });
  return subscription;
}

export async function unsubscribeFromPush(userEmail) {
  const subscription = await getExistingSubscription();
  if (!subscription) return;
  const endpoint = subscription.endpoint;
  await subscription.unsubscribe();
  await api.unsubscribePush(userEmail, endpoint);
}
