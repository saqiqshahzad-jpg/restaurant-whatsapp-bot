// WhatsApp Cloud API Test Utility for Restaurant Food Ordering Bot
const token = process.env.WHATSAPP_ACCESS_TOKEN || 'YOUR_ACCESS_TOKEN';
const restaurant_id = process.env.WHATSAPP_PHONE_NUMBER_ID || '1290949397435766';
const to_phone = process.env.WHATSAPP_RECIPIENT_PHONE || '923228801436';

const message = `Assalam o Alaikum! Khush amdeed! 🍔🍕 Humare restaurant mein aapka order ready karne ke liye hum hazir hain. Aap menu dekhna chahte hain ya apna order place karna chahte hain?`;

async function sendMessage() {
  try {
    const res = await fetch(`https://graph.facebook.com/v25.0/${restaurant_id}/messages`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        messaging_product: 'whatsapp',
        to: to_phone,
        type: 'text',
        text: { body: message }
      })
    });
    const data = await res.json();
    console.log('Order Bot Message sent. Status:', data.messages ? 'Success' : data);
  } catch (err) {
    console.error('Error sending message:', err);
  }
}

sendMessage();
