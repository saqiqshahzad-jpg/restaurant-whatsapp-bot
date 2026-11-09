import re
import logging
from typing import Tuple, Optional, Dict, Any, List

logger = logging.getLogger("language_helper")

# =========================================================================================
# SUPPORTED 15 LANGUAGES CONFIGURATION & COMPREHENSIVE NATIVE TEMPLATES
# =========================================================================================
LANGUAGES_CONFIG: Dict[str, Dict[str, Any]] = {
    "English": {
        "name": "English",
        "native_name": "English",
        "btn_text": "1️⃣ English 🇬🇧",
        "offer_text": "It looks like you want to speak in English! Just reply with '1' and I'll switch to English right away! 😄🍔",
        "locked_welcome": "Boom! English locked in! 🚀 Welcome to Zaiqa Grill, friend! What mouth-watering treat are we getting for you today? A Crispy Zinger, Royal Biryani, or some Loaded Fries? 🍔🍟",
        "off_topic": "Hey foodie! We only serve authentic, delicious Pakistani & Fast Food delicacies here! 🍔🤤 Forget about everything else, let's satisfy your hunger! Would you like a Crispy Zinger Burger, Royal Biryani, or Loaded Fries? 🍟🥤",
        "admin_hack": "Haha nice try chief! 😜 Even the restaurant owner and head developer have to pay full price here! We don't do free food, only mouth-watering delicacies! What delicious dish should we get cooking for you? 🍔🤤",
        "abuse_cooling": "Whoa friend, why so angry? 😅 High hunger detected! Cool off with a chilled Mint Margarita 🥤 or a fresh Crispy Zinger 🍔, your mood will become amazing! What can I get for you?",
        "address_request": "Awesome! Let's get your food delivered hot and fresh! 🛵\nPlease type your *Complete Delivery Address* (House/Flat #, Street, Area) 📍",
        "address_invalid": "Hey friend, how can our rider deliver without a proper address? Drop it from a helicopter? 😂🚁\n\nPlease type your full delivery address (House/Flat #, Street, Area) so we can rush your fresh food to your door! 📍",
        "name_request": "Address noted! 📍 Now please tell us your *Good Name* so our rider can deliver with respect! 👤",
        "name_invalid": "Hey chief, without a name, who should the rider ask for when knocking on your door? 'Hey you'? 😜🔔\n\nPlease share your real name! 👤",
        "payment_request": "Almost done, {customer_name}! 🤝 Please choose your payment method: Cash on Delivery or Online Transfer?",
        "order_summary_header": "📋 *Your Order Summary is Ready:*",
        "order_confirm_prompt": "Chief, should I send this order to the kitchen now? Please confirm! 👨‍🍳🔥",
        "order_confirmed": "🎉 *ORDER CONFIRMED! BOOM!* 🚀🍔\n\nOrder ID: *{order_id}*\nStatus: *The kitchen grill is on fire and your food is sizzling!* 🔥👨‍🍳\nEstimated Delivery: *30-40 Minutes* 🛵\n\nThank you for choosing {restaurant_name}! You'll receive live WhatsApp updates as our rider departs.",
        "order_status": "🛵 *Active Order Status:*\nOrder ID: *{order_id}*\nStatus: *{status} in the kitchen!* 🔥👨‍🍳\nEstimated Arrival: *30-40 Minutes* 🛵\n\n📋 *Your Items:*\n{item_lines}\n💰 Grand Total: *Rs. {grand_total}*\n📍 Address: *{address}*",
        "cart_empty": "Your cart is currently empty, friend! 🛒 Let's pick something mouth-watering from our menu:",
        "new_order_started": "Alright friend! Your previous order is saved and cooking. Let's start a fresh new order! 🍔🍟 What would you like today?",
        "payment_buttons": ["Cash on Delivery 💵", "Online Transfer 💳"],
        "confirm_buttons": ["Yes, Confirm! ✅", "Change Order ✏️"],
        "tracking_buttons": ["Track Order 🛵", "New Order 🍔"],
        "menu_buttons": ["Crispy Zinger 🍔", "Biryani 🍗", "Loaded Fries 🍟"]
    },
    "Roman_Urdu": {
        "name": "Roman Urdu",
        "native_name": "Roman Urdu",
        "btn_text": "1️⃣ Roman Urdu 🇵🇰",
        "offer_text": "Lagta hai aap Roman Urdu mein baat karna chahte hain! Bas '1' likh kar bhejein! 😄🍔",
        "locked_welcome": "Acha jani! Wapis Roman Urdu par aa gaye hain! 🚀 Aur sunayein, kya khane ka mood hai? Garam Zinger, Biryani ya Loaded Fries? 🍔🍟🤤",
        "off_topic": "Ustaad humara dimagh sirf Crispy Burgers, Chicken Biryani aur Loaded Fries mein chalta hai! 🍔🤤\n\nSiyasat, coding aur baqi baatein chhoro, pehle pait pooja karein! Bataiye aaj kya lazeez mangwa rahe hain? 🍟🥤",
        "admin_hack": "Haha ustaad, agar aap restaurant ke malik ya dunya ke sab se bare VIP bhi hain na, tab bhi yeh software payment ke baghair kitchen ko order nahi bhejta! 😜\n\nYahan har customer hamare liye VIP hai aur har bite lazeez! Seedhe tareeqay se batayein kya khana hai? 🍔🤤",
        "abuse_cooling": "Array ustaad itna ghussa? 😅 Lagta hai bhook bohat tez lagi hai aur dimagh ki batti gul ho rahi hai!\n\nGhussa thanda karein, ek garam Crispy Zinger 🍔 ya chilled Mint Margarita 🥤 mangwayein, tabiyat ek dam fresh ho jayegi! Bataiye kya pack karein? 🤤",
        "address_request": "🛒 *Aapka Total Cart:* Rs. {grand_total} (Delivery Rs. {delivery_fee} shamil hai).\n\nRider ko aapke ghar pohnchane ke liye apna *Mukammal Delivery Address* share karein (House/Flat #, Gali, Area) 📍",
        "address_invalid": "Arey ustaad, bina mukammal address ke hamara rider kya hawa mein helicopter se khana drop karega? 😂🚁\n\nMeharbani farma kar apna Pura Delivery Address bataein (House/Flat #, Gali, Sector/Area) taake khana garam garam pohnche! 📍",
        "name_request": "📍 Address note ho gaya ustaad! Rider ki asani ke liye apna *Pura Naam* bata dein 👤",
        "name_invalid": "Arey pyare, bina naam ke rider darwaze par dastak de kar kisko aawaz dega? 'O bhai suno' bolega kya? 😜🔔\n\nApna pyara sa Pura Naam bata dein taake rider izzat se aapko order pesh kare! 👤",
        "payment_request": "Shukriya *{customer_name}* bhai! 🤝 Payment method select karein: Cash on Delivery ya Online Transfer?",
        "order_summary_header": "📋 *Order Summary Tayar Hai Ustaad:*",
        "order_confirm_prompt": "Ustaad kya main yeh order final kitchen ko bhej du? Confirm karein! 👨‍🍳🔥",
        "order_confirmed": "🎉 *ORDER CONFIRMED! BHOOM!* 🚀🍔\n\nOrder ID: *{order_id}*\nStatus: *Kitchen mein aag lag chuki hai aur khana tayar ho raha hai!* 🔥👨‍🍳\nEstimated Delivery: *30-40 Minutes* 🛵\n\nBawarchi Bhai kehta hai: *Speed se delivery pohnche gi ustaad!* 😎\n*{restaurant_name}* ka intekhab karne ka shukriya! Rider nikalte hi aap ko WhatsApp par live update mil jayegi.",
        "order_status": "🛵 *Aapka Active Order Status:*\nOrder ID: *{order_id}*\nStatus: *Kitchen mein {status} ho raha hai!* 🔥👨‍🍳\nEstimated Delivery: *30-40 Minutes* 🛵\n\n📋 *Items:*\n{item_lines}\n💰 Grand Total: *Rs. {grand_total}*\n📍 Address: *{address}*",
        "cart_empty": "Aapka cart abhi bilkul khali hai jani! 🛒 Pehle menu mein se kuch lazeez pasand karein:",
        "new_order_started": "Chalo ustaad! Purana order kitchen mein pak raha hai, ab naya order shuru karte hain! 🍔🍟 Aaj kya khana pasand karein ge?",
        "payment_buttons": ["Cash on Delivery 💵", "Online Transfer 💳"],
        "confirm_buttons": ["Haan, Confirm ✅", "Change Order ✏️"],
        "tracking_buttons": ["Track Order 🛵", "Naya Order 🍔"],
        "menu_buttons": ["Crispy Zinger 🍔", "Biryani 🍗", "Loaded Fries 🍟"]
    },
    "Urdu_Script": {
        "name": "Urdu (اردو)",
        "native_name": "اردو",
        "btn_text": "1️⃣ اردو 🇵🇰",
        "offer_text": "لگتا ہے آپ اردو رسم الخط میں بات کرنا چاہتے ہیں! بس '1' لکھ کر بھیجیں، میں اردو میں بات کروں گا! 😄🍔",
        "locked_welcome": "زبردست! اردو زبان منتخب ہو گئی ہے! 🚀 ذائقہ گرل میں خوش آمدید! آج کیا کھانا پسند کریں گے؟ 🍔🍟",
        "off_topic": "استاد جی! ہمارا دھیان صرف مزیدار کھانوں، کرسپی زنگر اور بریانی پر ہے! 🍔🤤 دنیا کی فکر چھوڑیں، پہلے پیٹ پوجا کریں! بتائیے کیا منگوانا ہے؟ 🍟🥤",
        "admin_hack": "ہا ہا استاد جی! یہاں مالک ہو یا وی آئی پی، بنا بل کے کچن سے نوالہ نہیں نکلتا! 😜 آپ بتائیے کیا لذیذ تیار کروائیں؟ 🍔🤤",
        "abuse_cooling": "ارے جناب اتنا غصہ؟ 😅 لگتا ہے بھوک بہت تیز لگی ہے! ٹھنڈی منٹ مارگریٹا یا گرما گرم زنگر کھائیں، موڈ ایک دم خوشگوار ہو جائے گا! 🍔🥤",
        "address_request": "بہترین! اپنا مکمل ڈیلیوری ایڈریس (گھر/فلیٹ نمبر، گلی، علاقہ) تحریر فرمائیں 📍",
        "address_invalid": "ارے استاد! بنا پتے کے رائیڈر کیا ہیلی کاپٹر سے کھانا پھینکے گا؟ 😂 اپنا پورا ایڈریس لکھیں تاکہ کھانا گرم پہنچ سکے! 📍",
        "name_request": "ایڈریس نوٹ ہو گیا! 📍 اب برائے مہربانی اپنا *پورا نام* بتائیں 👤",
        "name_invalid": "پیارے بھائی، بنا نام کے رائیڈر دروازے پر کس کو بلائے گا؟ 😜 اپنا پیارا سا نام بتا دیں! 👤",
        "payment_request": "شکریہ {customer_name} صاحب! 🤝 ادائیگی کا طریقہ منتخب کریں: کیش آن ڈیلیوری یا آن لائن ٹرانسفر؟",
        "order_summary_header": "📋 *آپ کے آرڈر کا خلاصہ تیار ہے:*",
        "order_confirm_prompt": "کیا میں یہ آرڈر کچن کو روانہ کر دوں؟ تصدیق فرمائیں! 👨‍🍳🔥",
        "order_confirmed": "🎉 *آرڈر کنفرم ہو گیا! زبردست!* 🚀🍔\n\nآرڈر آئی ڈی: *{order_id}*\nحالت: *کچن میں کھانا تیار ہو رہا ہے!* 🔥👨‍🍳\nمتوقع ڈیلیوری: *30-40 منٹ* 🛵\n\nذائقہ گرل منتخب کرنے کا شکریہ!",
        "order_status": "🛵 *آرڈر کی تفصیلات:*\nآرڈر آئی ڈی: *{order_id}*\nحالت: *کچن میں تیار ہو رہا ہے!* 🔥👨‍🍳\nمتوقع وقت: *30-40 منٹ* 🛵\n\n📋 *اشیاء:*\n{item_lines}\n💰 کل رقم: *Rs. {grand_total}*\n📍 پتہ: *{address}*",
        "cart_empty": "آپ کا کارٹ ابھی خالی ہے! 🛒 پہلے مینو سے کوئی لذیذ کھانا پسند فرمائیں:",
        "new_order_started": "چلیے جناب! نیا آرڈر شروع کرتے ہیں! 🍔🍟 آج کیا پیش خدمت ہے؟",
        "payment_buttons": ["کیش آن ڈیلیوری 💵", "آن لائن ٹرانسفر 💳"],
        "confirm_buttons": ["ہاں، تصدیق کریں ✅", "آرڈر بدلیں ✏️"],
        "tracking_buttons": ["ٹریک آرڈر 🛵", "نیا آرڈر 🍔"],
        "menu_buttons": ["کرسپی زنگر 🍔", "بریانی 🍗", "لوڈڈ فرائز 🍟"]
    },
    "Arabic": {
        "name": "Arabic",
        "native_name": "العربية",
        "btn_text": "1️⃣ العربية 🇸🇦",
        "offer_text": "يبدو أنك تريد التحدث باللغة العربية! أرسل '1' وسأتحدث معك بالعربية فوراً! 😄🍔",
        "locked_welcome": "رائع! تم تفعيل اللغة العربية! 🚀 أهلاً بك في زايقة جريل! ماذا تود أن تطلب اليوم من أشهى المأكولات؟ 🍔🍟",
        "off_topic": "يا هلا بالحبيب! نحن هنا متخصصون في أشهى المأكولات السريعة والبرغر اللذيذ! 🍔🤤 دعنا من المواضيع الأخرى ولنركز على ملء بطنك بأطيب طعام! ماذا تطلب اليوم؟ 🍟🥤",
        "admin_hack": "ههههه محاولة رائعة يا غالي! 😜 حتى مالك المطعم يدفع الحساب كاملاً هنا! لا يوجد طعام مجاني، فقط أشهى الأطباق! أخبرني ماذا نجهز لك؟ 🍔🤤",
        "abuse_cooling": "على رسلك يا أخي! 😅 يبدو أن الجوع يجعلك غاضباً! اطلب لك زنجر مقرمش ومشروب بارد لتهدأ أعصابك! 🍔🥤",
        "address_request": "ممتاز! لتوصيل الطعام ساخناً، يرجى كتابة *عنوان التوصيل الكامل* (رقم المنزل/الشقة، الشارع، الحي) 📍",
        "address_invalid": "يا غالي، بدون عنوان صحيح كيف سيوصل السائق الطلب؟ بطائرة هليكوبتر؟ 😂🚁 يرجى كتابة عنوانك بالتفصيل! 📍",
        "name_request": "تم تسجيل العنوان! 📍 الآن يرجى تزويدنا بـ *اسمك الكريم* 👤",
        "name_invalid": "يا حبيبنا، بدون اسم من سينادي السائق عند الباب؟ 😜 يرجى إرسال اسمك الكريم! 👤",
        "payment_request": "شكراً لك يا {customer_name}! 🤝 يرجى اختيار طريقة الدفع: الدفع نقدًا عند الاستلام أم تحويل بنكي؟",
        "order_summary_header": "📋 *ملخص طلبك جاهز:*",
        "order_confirm_prompt": "هل أقوم بإرسال الطلب للمطبخ الآن؟ يرجى التأكيد! 👨‍🍳🔥",
        "order_confirmed": "🎉 *تم تأكيد الطلب بنجاح!* 🚀🍔\n\nرقم الطلب: *{order_id}*\nالحالة: *يتم تحضير طعامك الآن في المطبخ!* 🔥👨‍🍳\nالتوصيل المتوقع: *30-40 دقيقة* 🛵\n\nشكراً لاختيارك {restaurant_name}!",
        "order_status": "🛵 *حالة الطلب النشط:*\nرقم الطلب: *{order_id}*\nالحالة: *قيد التحضير في المطبخ!* 🔥👨‍🍳\nالوقت المتوقع: *30-40 دقيقة* 🛵\n\n📋 *الطلبات:*\n{item_lines}\n💰 المجموع الكلي: *Rs. {grand_total}*\n📍 العنوان: *{address}*",
        "cart_empty": "سلة طلباتك فارغة حالياً! 🛒 اختر وجبتك اللذيذة من القائمة أولاً:",
        "new_order_started": "على بركة الله! تم حفظ الطلب السابق وجاري تحضيره. لنبدأ طلباً جديداً! 🍔🍟 ماذا تشتهي اليوم؟",
        "payment_buttons": ["الدفع نقدًا 💵", "تحويل بنكي 💳"],
        "confirm_buttons": ["تأكيد الطلب ✅", "تعديل الطلب ✏️"],
        "tracking_buttons": ["تتبع الطلب 🛵", "طلب جديد 🍔"],
        "menu_buttons": ["كريسبي زنجر 🍔", "برياني ملكي 🍗", "بطاطس محملة 🍟"]
    },
    "Hindi": {
        "name": "Hindi",
        "native_name": "हिन्दी",
        "btn_text": "1️⃣ हिन्दी 🇮🇳",
        "offer_text": "लगता है आप हिन्दी में बात करना चाहते हैं! बस '1' लिखकर भेजें, मैं हिन्दी में बात करूँगा! 😄🍔",
        "locked_welcome": "शानदार! हिन्दी लॉक हो गई! 🚀 ज़ायका ग्रिल में आपका स्वागत है! आज क्या खाना पसंद करेंगे? 🍔🍟",
        "off_topic": "दोस्त, हमारा ध्यान सिर्फ लज़ीज़ बर्गर, चिकन बिरयानी और लोडेड फ्राइज़ पर है! 🍔🤤 बाकी सब छोड़िए, पहले पेट पूजा कीजिए! बताइए क्या मंगवाएं? 🍟🥤",
        "admin_hack": "हाहा क्या बात है दोस्त! 😜 लेकिन यहाँ खुद मालिक को भी पूरा बिल भरना पड़ता है! फ्री कुछ नहीं, सिर्फ स्वाद मिलेगा! बताइए क्या ऑर्डर करें? 🍔🤤",
        "abuse_cooling": "अरे भाई इतना गुस्सा क्यों? 😅 लगता है बहुत तेज़ भूख लगी है! एक क्रिस्पी ज़िंगर और ठंडा मिंट मार्गरीटा पीजिए, मिज़ाज तरोताज़ा हो जाएगा! 🍔🥤",
        "address_request": "शानदार! अपना *पूरा डिलीवरी पता* लिखें (मकान/फ्लैट #, गली, क्षेत्र) 📍",
        "address_invalid": "अरे भाई, बिना पते के राइडर क्या हेलीकॉप्टर से खाना गिराएगा? 😂 कृपया पूरा पता लिखें ताकि खाना गरमा-गरम पहुँचे! 📍",
        "name_request": "पता नोट हो गया! 📍 अब राइडर की आसानी के लिए अपना *शुभ नाम* बताइए 👤",
        "name_invalid": "अरे प्यारे दोस्त, बिना नाम के राइडर दरवाज़े पर किसे आवाज़ देगा? 😜 अपना शुभ नाम बता दीजिए! 👤",
        "payment_request": "धन्यवाद {customer_name} जी! 🤝 पेमेंट का तरीका चुनें: कैश ऑन डिलीवरी या ऑनलाइन ट्रांसफर?",
        "order_summary_header": "📋 *आपके ऑर्डर का सारांश तैयार है:*",
        "order_confirm_prompt": "क्या यह ऑर्डर किचन में भेज दिया जाए? कृपया कन्फर्म करें! 👨‍🍳🔥",
        "order_confirmed": "🎉 *ऑर्डर कन्फर्म हो गया! बूम!* 🚀🍔\n\nऑर्डर आईडी: *{order_id}*\nस्थिति: *किचन में खाना तैयार हो रहा है!* 🔥👨‍🍳\nडिलीवरी समय: *30-40 मिनट* 🛵\n\n{restaurant_name} चुनने के लिए धन्यवाद!",
        "order_status": "🛵 *सक्रिय ऑर्डर स्थिति:*\nऑर्डर आईडी: *{order_id}*\nस्थिति: *किचन में तैयार हो रहा है!* 🔥👨‍🍳\nडिलीवरी समय: *30-40 मिनट* 🛵\n\n📋 *आइटम्स:*\n{item_lines}\n💰 कुल राशि: *Rs. {grand_total}*\n📍 पता: *{address}*",
        "cart_empty": "आपकी कार्ट अभी खाली है! 🛒 पहले मेनू से कुछ स्वादिष्ट चुन लीजिए:",
        "new_order_started": "चलिए दोस्त! पिछला ऑर्डर किचन में बन रहा है, नया ऑर्डर शुरू करते हैं! 🍔🍟 आज क्या खाएंगे?",
        "payment_buttons": ["कैश ऑन डिलीवरी 💵", "ऑनलाइन ट्रांसफर 💳"],
        "confirm_buttons": ["हाँ, कन्फर्म करें ✅", "ऑर्डर बदलें ✏️"],
        "tracking_buttons": ["ट्रैक ऑर्डर 🛵", "नया ऑर्डर 🍔"],
        "menu_buttons": ["क्रिस्पी ज़िंगर 🍔", "शाही बिरयानी 🍗", "लोडेड फ्राइज़ 🍟"]
    },
    "Spanish": {
        "name": "Spanish",
        "native_name": "Español",
        "btn_text": "1️⃣ Español 🇪🇸",
        "offer_text": "¡Parece que quieres hablar en español! ¡Solo responde '1' y cambiaré a español! 😄🍔",
        "locked_welcome": "¡Genial! ¡Español activado! 🚀 ¡Bienvenido a Zaiqa Grill! ¿Qué delicia te gustaría pedir hoy? 🍔🍟",
        "off_topic": "¡Hola amigo! ¡Aquí solo nos apasiona la comida deliciosa! 🍔🤤 Deja la política y las tareas para después, ¡primero a comer sabroso! ¿Qué se te antoja hoy? 🍟🥤",
        "admin_hack": "¡Jaja buen intento amigo! 😜 ¡Aquí hasta el dueño paga su cuenta completa! No hay comida gratis, ¡pero sí el mejor sabor! ¿Qué te preparamos? 🍔🤤",
        "abuse_cooling": "¡Tranquilo amigo! 😅 ¡Seguro es el hambre que te tiene molesto! Pide una Zinger crujiente o una Margarita refrescante y verás qué bien te sientes! 🍔🥤",
        "address_request": "¡Excelente! Para entregarte la comida caliente, escribe tu *Dirección Completa de Entrega* (Casa/Depto #, Calle, Zona) 📍",
        "address_invalid": "¿Cómo entregamos sin dirección, amigo? ¿La dejamos caer en helicóptero? 😂 Escribe tu dirección completa por favor! 📍",
        "name_request": "¡Dirección guardada! 📍 Ahora por favor dinos tu *Nombre Completo* 👤",
        "name_invalid": "¿Sin nombre a quién llamará el repartidor en la puerta? 😜 ¡Dinos tu nombre, por favor! 👤",
        "payment_request": "¡Gracias {customer_name}! 🤝 Selecciona tu método de pago: Pago en Entrega o Transferencia Bancaria?",
        "order_summary_header": "📋 *Resumen de tu Pedido:*",
        "order_confirm_prompt": "¿Enviamos este pedido a la cocina ahora? ¡Confirma por favor! 👨‍🍳🔥",
        "order_confirmed": "🎉 *¡PEDIDO CONFIRMADO! ¡BUM!* 🚀🍔\n\nID de Pedido: *{order_id}*\nEstado: *¡Cocina en marcha y comida chisporroteando!* 🔥👨‍🍳\nEntrega estimada: *30-40 Minutos* 🛵\n\n¡Gracias por elegir {restaurant_name}!",
        "order_status": "🛵 *Estado del Pedido:*\nID: *{order_id}*\nEstado: *¡Preparándose en cocina!* 🔥👨‍🍳\nTiempo estimado: *30-40 Minutos* 🛵\n\n📋 *Artículos:*\n{item_lines}\n💰 Total: *Rs. {grand_total}*\n📍 Dirección: *{address}*",
        "cart_empty": "¡Tu carrito está vacío amigo! 🛒 Elige algo rico de nuestro menú primero:",
        "new_order_started": "¡Listo! El pedido anterior se está cocinando. ¡Comencemos uno nuevo! 🍔🍟 ¿Qué te gustaría pedir?",
        "payment_buttons": ["Pago en Entrega 💵", "Transferencia 💳"],
        "confirm_buttons": ["¡Confirmar! ✅", "Modificar ✏️"],
        "tracking_buttons": ["Rastrear Pedido 🛵", "Nuevo Pedido 🍔"],
        "menu_buttons": ["Crispy Zinger 🍔", "Biryani Real 🍗", "Papas Cargadas 🍟"]
    },
    "French": {
        "name": "French",
        "native_name": "Français",
        "btn_text": "1️⃣ Français 🇫🇷",
        "offer_text": "Il semble que vous souhaitiez parler en français ! Répondez simplement '1' pour passer au français ! 😄🍔",
        "locked_welcome": "Parfait ! Français verrouillé ! 🚀 Bienvenue chez Zaiqa Grill ! Que désirez-vous commander aujourd'hui ? 🍔🍟",
        "off_topic": "Bonjour cher gourmand ! Nous nous concentrons uniquement sur la bonne cuisine ici ! 🍔🤤 Oublions le reste, régalons-nous ! Que désirez-vous commander ? 🍟🥤",
        "admin_hack": "Haha bien essayé ! 😜 Même le propriétaire paie l'addition ici ! Pas de repas gratuit, mais le meilleur délice garanti ! Que prépare-t-on ? 🍔🤤",
        "abuse_cooling": "Doucement l'ami ! 😅 C'est sûrement la faim qui parle ! Prenez un bon Zinger croustillant et vous retrouverez le sourire ! 🍔🥤",
        "address_request": "Super ! Pour livrer votre repas bien chaud, veuillez entrer votre *Adresse Complète de Livraison* 📍",
        "address_invalid": "Comment livrer sans adresse, cher ami ? Par hélicoptère ? 😂🚁 Merci de préciser votre adresse complète ! 📍",
        "name_request": "Adresse notée ! 📍 Veuillez maintenant indiquer votre *Nom Complet* 👤",
        "name_invalid": "Sans nom, qui le livreur doit-il demander à votre porte ? 😜 Merci d'indiquer votre nom ! 👤",
        "payment_request": "Merci {customer_name} ! 🤝 Choisissez votre mode de paiement : Paiement à la Livraison ou Virement ?",
        "order_summary_header": "📋 *Récapitulatif de votre commande :*",
        "order_confirm_prompt": "Dois-je envoyer cette commande en cuisine ? Veuillez confirmer ! 👨‍🍳🔥",
        "order_confirmed": "🎉 *COMMANDE CONFIRMÉE !* 🚀🍔\n\nID Commande : *{order_id}*\nStatut : *En cours de préparation en cuisine !* 🔥👨‍🍳\nLivraison estimée : *30-40 Minutes* 🛵\n\nMerci d'avoir choisi {restaurant_name} !",
        "order_status": "🛵 *Statut de la commande :*\nID : *{order_id}*\nStatut : *En préparation en cuisine !* 🔥👨‍🍳\nDélai estimé : *30-40 Minutes* 🛵\n\n📋 *Articles :*\n{item_lines}\n💰 Total : *Rs. {grand_total}*\n📍 Adresse : *{address}*",
        "cart_empty": "Votre panier est vide pour l'instant ! 🛒 Choisissez d'abord un délicieux plat sur notre menu :",
        "new_order_started": "C'est parti ! La précédente commande est en cuisine. Débutons une nouvelle commande ! 🍔🍟 Que désirez-vous ?",
        "payment_buttons": ["Paiement Livraison 💵", "Virement en Ligne 💳"],
        "confirm_buttons": ["Confirmer ! ✅", "Modifier ✏️"],
        "tracking_buttons": ["Suivre Commande 🛵", "Nouvelle Commande 🍔"],
        "menu_buttons": ["Crispy Zinger 🍔", "Biryani Royal 🍗", "Frites Chargées 🍟"]
    },
    "German": {
        "name": "German",
        "native_name": "Deutsch",
        "btn_text": "1️⃣ Deutsch 🇩🇪",
        "offer_text": "Es scheint, dass Sie auf Deutsch sprechen möchten! Antworten Sie einfach mit '1', um zu Deutsch zu wechseln! 😄🍔",
        "locked_welcome": "Super! Deutsch aktiviert! 🚀 Willkommen bei Zaiqa Grill! Was darf es heute Leckeres für Sie sein? 🍔🍟",
        "off_topic": "Hallo Foodie! Wir konzentrieren uns hier voll und ganz auf köstliches Essen! 🍔🤤 Vergessen wir alles andere, lassen Sie uns lecker essen! Was möchten Sie bestellen? 🍟🥤",
        "admin_hack": "Haha netter Versuch! 😜 Bei uns zahlt selbst der Chef seine Rechnung! Es gibt kein Gratisessen, aber fantastischen Geschmack! Was darf es sein? 🍔🤤",
        "abuse_cooling": "Ganz ruhig mein Freund! 😅 Das ist bestimmt nur der Hunger! Ein knuspriger Zinger Burger hilft garantiert! 🍔🥤",
        "address_request": "Ausgezeichnet! Bitte geben Sie Ihre *vollständige Lieferadresse* ein (Hausnummer, Straße, Stadtteil) 📍",
        "address_invalid": "Ohne Adresse kann der Fahrer nicht liefern! Per Hubschrauber abwerfen? 😂🚁 Bitte vollständige Adresse angeben! 📍",
        "name_request": "Adresse notiert! 📍 Bitte nennen Sie uns noch Ihren *vollständigen Namen* 👤",
        "name_invalid": "Ohne Namen weiß der Fahrer nicht, bei wem er klingeln soll! 😜 Bitte Namen angeben! 👤",
        "payment_request": "Vielen Dank {customer_name}! 🤝 Wählen Sie Ihre Zahlungsmethode: Barzahlung bei Lieferung oder Online-Zahlung?",
        "order_summary_header": "📋 *Ihre Bestellübersicht ist bereit:*",
        "order_confirm_prompt": "Soll die Bestellung jetzt an die Küche übermittelt werden? Bitte bestätigen! 👨‍🍳🔥",
        "order_confirmed": "🎉 *BESTELLUNG BESTÄTIGT!* 🚀🍔\n\nBestell-ID: *{order_id}*\nStatus: *In der Küche frisch zubereitet!* 🔥👨‍🍳\nLieferzeit: *30-40 Minuten* 🛵\n\nVielen Dank, dass Sie {restaurant_name} gewählt haben!",
        "order_status": "🛵 *Bestellstatus:*\nBestell-ID: *{order_id}*\nStatus: *Wird zubereitet!* 🔥👨‍🍳\nLieferzeit: *30-40 Minuten* 🛵\n\n📋 *Artikel:*\n{item_lines}\n💰 Gesamtbetrag: *Rs. {grand_total}*\n📍 Adresse: *{address}*",
        "cart_empty": "Ihr Warenkorb ist derzeit leer! 🛒 Wählen Sie zuerst etwas Leckeres aus unserer Speisekarte:",
        "new_order_started": "Alles klar! Vorherige Bestellung ist in der Küche. Starten wir eine neue Bestellung! 🍔🍟 Was darf es sein?",
        "payment_buttons": ["Barzahlung 💵", "Online-Zahlung 💳"],
        "confirm_buttons": ["Bestätigen! ✅", "Ändern ✏️"],
        "tracking_buttons": ["Verfolgen 🛵", "Neue Bestellung 🍔"],
        "menu_buttons": ["Crispy Zinger 🍔", "Biryani 🍗", "Loaded Fries 🍟"]
    },
    "Turkish": {
        "name": "Turkish",
        "native_name": "Türkçe",
        "btn_text": "1️⃣ Türkçe 🇹🇷",
        "offer_text": "Türkçe konuşmak istiyorsunuz gibi görünüyor! Türkçe'ye geçmek için '1' yazmanız yeterli! 😄🍔",
        "locked_welcome": "Harika! Türkçe kilitlendi! 🚀 Zaiqa Grill'e hoş geldiniz! Bugün ne sipariş etmek istersiniz? 🍔🍟",
        "off_topic": "Selamlar! Biz burada sadece enfes lezzetlere odaklanıyoruz! 🍔🤤 Diğer konuları boşverin, önce karnımızı doyuralım! Ne ikram edelim? 🍟🥤",
        "admin_hack": "Haha güzel deneme! 😜 Bizde restoranın sahibi bile tam hesap öder! Bedava yemek yok ama en üstün lezzet var! Ne hazırlayalım? 🍔🤤",
        "abuse_cooling": "Sakin ol dostum! 😅 Bu kesin açlıktan! Çıtır bir Zinger Burger veya buz gibi içecekle keyfin yerine gelsin! 🍔🥤",
        "address_request": "Harika! Sıcak teslimat için lütfen *Açık Teslimat Adresinizi* yazın (Bina/Daire #, Sokak, Mahalle) 📍",
        "address_invalid": "Adres olmadan kurye havadan mı atsın dostum? 😂🚁 Lütfen tam adresinizi yazın! 📍",
        "name_request": "Adres kaydedildi! 📍 Şimdi kuryemizin size hitap edebilmesi için *Adınızı* yazın 👤",
        "name_invalid": "İsim olmadan kurye kapıyı çalınca kime seslensin? 😜 Lütfen adınızı yazın! 👤",
        "payment_request": "Teşekkürler {customer_name}! 🤝 Ödeme yönteminizi seçin: Kapıda Ödeme mi Online Transfer mi?",
        "order_summary_header": "📋 *Sipariş Özetiniz Hazır:*",
        "order_confirm_prompt": "Siparişi hemen mutfağa ileteyim mi? Lütfen onaylayın! 👨‍🍳🔥",
        "order_confirmed": "🎉 *SİPARİŞ ONAYLANDI!* 🚀🍔\n\nSipariş No: *{order_id}*\nDurum: *Mutfakta ateş yandı ve hazırlanıyor!* 🔥👨‍🍳\nTahmini Teslimat: *30-40 Dakika* 🛵\n\n{restaurant_name}'i tercih ettiğiniz için teşekkürler!",
        "order_status": "🛵 *Aktif Sipariş Durumu:*\nSipariş No: *{order_id}*\nDurum: *Mutfakta hazırlanıyor!* 🔥👨‍🍳\nTahmini Süre: *30-40 Dakika* 🛵\n\n📋 *Ürünler:*\n{item_lines}\n💰 Toplam: *Rs. {grand_total}*\n📍 Adres: *{address}*",
        "cart_empty": "Sepetiniz şu an boş! 🛒 Önce menümüzden leziz bir şeyler seçin:",
        "new_order_started": "Harika! Önceki sipariş mutfakta pişiyor. Yeni bir siparişe başlayalım! 🍔🍟 Bugün ne istersiniz?",
        "payment_buttons": ["Kapıda Ödeme 💵", "Online Transfer 💳"],
        "confirm_buttons": ["Onayla! ✅", "Değiştir ✏️"],
        "tracking_buttons": ["Siparişi Takip Et 🛵", "Yeni Sipariş 🍔"],
        "menu_buttons": ["Crispy Zinger 🍔", "Özel Biryani 🍗", "Dolu Patates 🍟"]
    },
    "Russian": {
        "name": "Russian",
        "native_name": "Русский",
        "btn_text": "1️⃣ Русский 🇷🇺",
        "offer_text": "Похоже, вы хотите общаться на русском! Просто ответьте '1', и я переключусь на русский язык! 😄🍔",
        "locked_welcome": "Отлично! Русский язык включен! 🚀 Добро пожаловать в Zaiqa Grill! Что вкусненького для вас приготовить? 🍔🍟",
        "off_topic": "Привет гурманам! Здесь мы думаем только о сочных бургерах и вкусной еде! 🍔🤤 Оставим прочие дела, давайте вкусно поедим! Что закажете? 🍟🥤",
        "admin_hack": "Ха-ха, отличная попытка! 😜 У нас даже владелец заведения платит по счёту! Бесплатной еды нет, но вкус — высший класс! Что готовить? 🍔🤤",
        "abuse_cooling": "Спокойнее, друг! 😅 Это точно от голода! Горячий Криспи Зингер и прохладный напиток мигом поднимут настроение! 🍔🥤",
        "address_request": "Превосходно! Чтобы доставить заказ горячим, напишите ваш *полный адрес доставки* (дом/квартира, улица, район) 📍",
        "address_invalid": "Без адреса курьер еду с вертолёта сбросит? 😂🚁 Напишите полный адрес, пожалуйста! 📍",
        "name_request": "Адрес записан! 📍 Теперь напишите ваше *имя* 👤",
        "name_invalid": "Без имени курьер не узнает, кому передать заказ! 😜 Напишите ваше имя, пожалуйста! 👤",
        "payment_request": "Спасибо, {customer_name}! 🤝 Выберите способ оплаты: Оплата курьеру или Онлайн-перевод?",
        "order_summary_header": "📋 *Ваш заказ сформирован:*",
        "order_confirm_prompt": "Отправляем заказ на кухню? Подтвердите, пожалуйста! 👨‍🍳🔥",
        "order_confirmed": "🎉 *ЗАКАЗ ПОДТВЕРЖДЁН!* 🚀🍔\n\nНомер заказа: *{order_id}*\nСтатус: *Готовится на кухне!* 🔥👨‍🍳\nДоставка: *30-40 минут* 🛵\n\nСпасибо, что выбрали {restaurant_name}!",
        "order_status": "🛵 *Статус заказа:*\nНомер заказа: *{order_id}*\nСтатус: *Готовится на кухне!* 🔥👨‍🍳\nВремя доставки: *30-40 минут* 🛵\n\n📋 *Состав:*\n{item_lines}\n💰 Итого: *Rs. {grand_total}*\n📍 Адрес: *{address}*",
        "cart_empty": "Ваша корзина пуста! 🛒 Выберите что-нибудь аппетитное из нашего меню:",
        "new_order_started": "Отлично! Прошлый заказ уже на кухне. Начнём новый заказ! 🍔🍟 Что хотите выбрать?",
        "payment_buttons": ["Оплата курьеру 💵", "Онлайн-перевод 💳"],
        "confirm_buttons": ["Подтвердить! ✅", "Изменить ✏️"],
        "tracking_buttons": ["Отследить заказ 🛵", "Новый заказ 🍔"],
        "menu_buttons": ["Криспи Зингер 🍔", "Бирьяни 🍗", "Картофель фри 🍟"]
    },
    "Chinese": {
        "name": "Chinese",
        "native_name": "中文",
        "btn_text": "1️⃣ 中文 🇨🇳",
        "offer_text": "看来您想用中文交流！只需回复“1”，我将立即切换为中文！😄🍔",
        "locked_welcome": "太棒了！中文已锁定！🚀 欢迎光临 Zaiqa Grill！今天想吃点什么美味？ 🍔🍟",
        "off_topic": "吃货朋友您好！我们全心全意为您制作正宗美味的炸鸡汉堡与香饭！🍔🤤 其他事情先放一边，吃饱最要紧！今天想尝尝什么？ 🍟🥤",
        "admin_hack": "哈哈真幽默！😜 在我们店里，就连老板也要全额买单哦！没有免费餐，但保证每一口都香脆可口！快告诉我您想吃什么？ 🍔🤤",
        "abuse_cooling": "消消气朋友！😅 肚子饿了确实容易着急！来一份香脆劲脆堡和冰镇薄荷饮，心情马上变好！ 🍔🥤",
        "address_request": "太好了！为了趁热送达，请输入您的*详细送餐地址*（门牌号/公寓、街道、区域）📍",
        "address_invalid": "朋友，没有准确地址外卖小哥没法送呀，总不能用直升机空投吧？😂🚁 请提供完整地址！ 📍",
        "name_request": "地址已记录！📍 请问如何称呼您？请输入您的*姓名* 👤",
        "name_invalid": "没有姓名小哥敲门该找谁呢？😜 请留下您的姓名！ 👤",
        "payment_request": "谢谢您，{customer_name}！🤝 请选择支付方式：货到付款 还是 在线支付？",
        "order_summary_header": "📋 *您的订单明细已生成：*",
        "order_confirm_prompt": "现在就将订单提交至后厨开做吗？请确认！ 👨‍🍳🔥",
        "order_confirmed": "🎉 *订单已确认！太棒了！* 🚀🍔\n\n订单号：*{order_id}*\n状态：*后厨已起火热油，正在全力制作！* 🔥👨‍🍳\n预计送达：*30-40 分钟* 🛵\n\n感谢您选择 {restaurant_name}！",
        "order_status": "🛵 *当前订单状态：*\n订单号：*{order_id}*\n状态：*后厨正在精心烹饪！* 🔥👨‍🍳\n预计送达：*30-40 分钟* 🛵\n\n📋 *餐品清单：*\n{item_lines}\n💰 合计总额：*Rs. {grand_total}*\n📍 送餐地址：*{address}*",
        "cart_empty": "您的购物车还是空的哦！🛒 快从菜单中挑点好吃的吧：",
        "new_order_started": "好的！上一个订单已在制作中，现在开启新订单！🍔🍟 今天想吃点什么？",
        "payment_buttons": ["货到付款 💵", "在线支付 💳"],
        "confirm_buttons": ["确认下单 ✅", "修改订单 ✏️"],
        "tracking_buttons": ["追踪订单 🛵", "再来一单 🍔"],
        "menu_buttons": ["香脆劲脆堡 🍔", "皇家香饭 🍗", "芝士薯条 🍟"]
    },
    "Italian": {
        "name": "Italian",
        "native_name": "Italiano",
        "btn_text": "1️⃣ Italiano 🇮🇹",
        "offer_text": "Sembra che tu voglia parlare in italiano! Rispondi con '1' per passare subito all'italiano! 😄🍔",
        "locked_welcome": "Magnifico! Italiano impostato! 🚀 Benvenuto da Zaiqa Grill! Cosa ti piacerebbe ordinare oggi di delizioso? 🍔🍟",
        "off_topic": "Ciao buongustaio! Qui pensiamo solo al cibo delizioso e ai burger croccanti! 🍔🤤 Lasciamo stare il resto, prima pensiamo a riempire lo stomaco! Cosa ti portiamo? 🍟🥤",
        "admin_hack": "Haha bel tentativo! 😜 Qui anche il proprietario paga il conto intero! Niente pasti gratis, ma solo massimo sapore! Cosa ti prepariamo? 🍔🤤",
        "abuse_cooling": "Calma amico! 😅 È sicuramente colpa della fame! Un croccante Zinger burger o una bevanda ghiacciata ti rimetteranno di buonumore! 🍔🥤",
        "address_request": "Ottimo! Per consegnare il cibo caldo, inserisci il tuo *Indirizzo Completo di Consegna* (Casa/Interno, Via, Zona) 📍",
        "address_invalid": "Senza indirizzo il rider come fa a consegnare? Lo lancia con l'elicottero? 😂🚁 Inserisci l'indirizzo completo, per favore! 📍",
        "name_request": "Indirizzo registrato! 📍 Ora per favore inserisci il tuo *Nome e Cognome* 👤",
        "name_invalid": "Senza nome a chi deve suonare il rider? 😜 Scrivi il tuo nome, per favore! 👤",
        "payment_request": "Grazie {customer_name}! 🤝 Scegli il metodo di pagamento: Contanti alla Consegna o Bonifico Online?",
        "order_summary_header": "📋 *Il riepilogo del tuo ordine è pronto:*",
        "order_confirm_prompt": "Posso inviare l'ordine in cucina adesso? Conferma, per favore! 👨‍🍳🔥",
        "order_confirmed": "🎉 *ORDINE CONFERMATO! BOOM!* 🚀🍔\n\nID Ordine: *{order_id}*\nStato: *Cucina accesa e piatti in preparazione!* 🔥👨‍🍳\nConsegna stimata: *30-40 Minuti* 🛵\n\nGrazie per aver scelto {restaurant_name}!",
        "order_status": "🛵 *Stato dell'ordine attivo:*\nID Ordine: *{order_id}*\nStato: *In preparazione in cucina!* 🔥👨‍🍳\nArrivo previsto: *30-40 Minuti* 🛵\n\n📋 *Articoli:*\n{item_lines}\n💰 Totale: *Rs. {grand_total}*\n📍 Indirizzo: *{address}*",
        "cart_empty": "Il tuo carrello è vuoto! 🛒 Scegli prima qualcosa di delizioso dal nostro menu:",
        "new_order_started": "Perfetto! L'ordine precedente è in cottura. Iniziamo un nuovo ordine! 🍔🍟 Cosa ti va oggi?",
        "payment_buttons": ["Contanti Consegna 💵", "Bonifico Online 💳"],
        "confirm_buttons": ["Conferma! ✅", "Modifica ✏️"],
        "tracking_buttons": ["Traccia Ordine 🛵", "Nuovo Ordine 🍔"],
        "menu_buttons": ["Crispy Zinger 🍔", "Biryani Reale 🍗", "Patatine 🍟"]
    },
    "Portuguese": {
        "name": "Portuguese",
        "native_name": "Português",
        "btn_text": "1️⃣ Português 🇵🇹",
        "offer_text": "Parece que você quer conversar em português! Responda '1' para mudar para português agora mesmo! 😄🍔",
        "locked_welcome": "Maravilha! Português ativado! 🚀 Bem-vindo ao Zaiqa Grill! Qual delícia você vai pedir hoje? 🍔🍟",
        "off_topic": "Olá amigo! Nosso foco aqui é comida deliciosa e suculenta! 🍔🤤 Vamos deixar outras coisas de lado e alimentar essa fome! O que vai ser hoje? 🍟🥤",
        "admin_hack": "Haha boa tentativa! 😜 Aqui até o dono paga a conta integral! Não tem comida de graça, mas tem muito sabor! O que vamos preparar? 🍔🤤",
        "abuse_cooling": "Calma amigo! 😅 Isso é fome falando alto! Peça um Zinger crocante e uma bebida gelada que o humor melhora na hora! 🍔🥤",
        "address_request": "Maravilha! Para entregar tudo quentinho, digite seu *Endereço Completo de Entrega* (Casa/Apt #, Rua, Bairro) 📍",
        "address_invalid": "Sem endereço o entregador vai jogar de helicóptero? 😂🚁 Por favor digite seu endereço completo! 📍",
        "name_request": "Endereço anotado! 📍 Agora informe seu *Nome Completo* para o entregador 👤",
        "name_invalid": "Sem nome o entregador vai chamar quem no portão? 😜 Diga seu nome por favor! 👤",
        "payment_request": "Obrigado {customer_name}! 🤝 Escolha a forma de pagamento: Pagamento na Entrega ou Transferência?",
        "order_summary_header": "📋 *Resumo do seu pedido pronto:*",
        "order_confirm_prompt": "Posso enviar este pedido para a cozinha agora? Confirme por favor! 👨‍🍳🔥",
        "order_confirmed": "🎉 *PEDIDO CONFIRMADO! BOOM!* 🚀🍔\n\nID do Pedido: *{order_id}*\nStatus: *Fogo aceso na cozinha e comida no ponto!* 🔥👨‍🍳\nEntrega estimada: *30-40 Minutos* 🛵\n\nObrigado por escolher o {restaurant_name}!",
        "order_status": "🛵 *Status do Pedido Ativo:*\nID do Pedido: *{order_id}*\nStatus: *Preparando na cozinha!* 🔥👨‍🍳\nTempo estimado: *30-40 Minutos* 🛵\n\n📋 *Itens:*\n{item_lines}\n💰 Total Geral: *Rs. {grand_total}*\n📍 Endereço: *{address}*",
        "cart_empty": "Seu carrinho está vazio! 🛒 Escolha algo delicioso em nosso cardápio primeiro:",
        "new_order_started": "Beleza! O pedido anterior está na cozinha. Vamos iniciar um novo pedido! 🍔🍟 O que deseja hoje?",
        "payment_buttons": ["Pagar na Entrega 💵", "Transferência 💳"],
        "confirm_buttons": ["Confirmar! ✅", "Alterar ✏️"],
        "tracking_buttons": ["Rastrear Pedido 🛵", "Novo Pedido 🍔"],
        "menu_buttons": ["Crispy Zinger 🍔", "Biryani Real 🍗", "Batatas 🍟"]
    },
    "Bengali": {
        "name": "Bengali",
        "native_name": "বাংলা",
        "btn_text": "1️⃣ বাংলা 🇧🇩",
        "offer_text": "মনে হচ্ছে আপনি বাংলায় কথা বলতে চান! শুধু '1' লিখে পাঠান, আমি বাংলায় কথা শুরু করব! 😄🍔",
        "locked_welcome": "দারুণ! বাংলা ভাষা সেট হয়েছে! 🚀 জাইকা গ্রিলে আপনাকে স্বাগতম! আজ কী সুস্বাদু খাবার খাবেন? 🍔🍟",
        "off_topic": "প্রিয় ভোজনরসিক! আমাদের নজর শুধু সুস্বাদু খাবার, ক্রিস্পি বার্গার আর বিরিয়ানির দিকে! 🍔🤤 অন্য কথা বাদ দিন, আগে পেট পূজা হোক! কী অর্ডার করবেন? 🍟🥤",
        "admin_hack": "হাহা দারুণ চেষ্টা! 😜 কিন্তু এখানে খোদ মালিককেও পুরো বিল দিতে হয়! ফ্রিতে কিছু নেই, তবে দুর্দান্ত স্বাদ পাবেন! কী বানিয়ে দেব বলুন? 🍔🤤",
        "abuse_cooling": "আরে ভাই এত রাগ কেন? 😅 পেটের ক্ষুধায় রাগ হওয়া স্বাভাবিক! একটা ক্রিস্পি জিঙ্গার আর ঠান্ডা মিন্ট মার্গারিটা খান, মেজাজ ফুরফুরে হয়ে যাবে! 🍔🥤",
        "address_request": "চমৎকার! গরম গরম খাবার পৌঁছে দেওয়ার জন্য আপনার *সম্পূর্ণ ডেলিভারি ঠিকানা* লিখুন 📍",
        "address_invalid": "ভাই ঠিকানা ছাড়া রাইডার কি হেলিকপ্টার থেকে খাবার ফেলবে? 😂🚁 দয়া করে সম্পূর্ণ ঠিকানা লিখুন! 📍",
        "name_request": "ঠিকানা নোট করা হয়েছে! 📍 এবার আপনার *পূর্ণ নাম* বলুন 👤",
        "name_invalid": "নাম ছাড়া রাইডার দরজায় এসে কাকে ডাকবে? 😜 দয়া করে আপনার সুন্দর নামটি বলুন! 👤",
        "payment_request": "ধন্যবাদ {customer_name}! 🤝 পেমেন্ট মেথড নির্বাচন করুন: ক্যাশ অন ডেলিভারি নাকি অনলাইন ট্রান্সফার?",
        "order_summary_header": "📋 *আপনার অর্ডারের বিবরণ প্রস্তুত:*",
        "order_confirm_prompt": "অর্ডারটি কি এখন রান্নাঘরে পাঠিয়ে দেব? নিশ্চিত করুন! 👨‍🍳🔥",
        "order_confirmed": "🎉 *অর্ডার নিশ্চিত হয়েছে! বুম!* 🚀🍔\n\nঅর্ডার আইডি: *{order_id}*\nস্ট্যাটাস: *রান্নাঘরে খাবার তৈরি হচ্ছে!* 🔥👨‍🍳\nআনুমানিক ডেলিভারি: *30-40 মিনিট* 🛵\n\n{restaurant_name} বেছে নেওয়ার জন্য ধন্যবাদ!",
        "order_status": "🛵 *অর্ডারের বর্তমান অবস্থা:*\nঅর্ডার আইডি: *{order_id}*\nস্ট্যাটাস: *রান্নাঘরে তৈরি হচ্ছে!* 🔥👨‍🍳\nআনুমানিক সময়: *30-40 মিনিট* 🛵\n\n📋 *আইটেমসমূহ:*\n{item_lines}\n💰 সর্বমোট বিল: *Rs. {grand_total}*\n📍 ঠিকানা: *{address}*",
        "cart_empty": "আপনার কার্ট বর্তমানে খালি! 🛒 মেনু থেকে আগে পছন্দের খাবার বেছে নিন:",
        "new_order_started": "ঠিক আছে! আগের অর্ডারটি রান্নাঘরে তৈরি হচ্ছে। চলুন নতুন অর্ডার শুরু করি! 🍔🍟 আজ কী খেতে চান?",
        "payment_buttons": ["ক্যাশ অন ডেলিভারি 💵", "অনলাইন ট্রান্সফার 💳"],
        "confirm_buttons": ["নিশ্চিত করুন ✅", "অর্ডার পরিবর্তন ✏️"],
        "tracking_buttons": ["ট্র্যাক অর্ডার 🛵", "নতুন অর্ডার 🍔"],
        "menu_buttons": ["ক্রিস্পি জিঙ্গার 🍔", "স্পেশাল বিরিয়ানি 🍗", "লোডেড ফ্রাই 🍟"]
    },
    "Indonesian": {
        "name": "Indonesian",
        "native_name": "Bahasa Indonesia",
        "btn_text": "1️⃣ Indonesia 🇮🇩",
        "offer_text": "Sepertinya Anda ingin menggunakan Bahasa Indonesia! Cukup balas '1' untuk beralih ke Bahasa Indonesia! 😄🍔",
        "locked_welcome": "Mantap! Bahasa Indonesia aktif! 🚀 Selamat datang di Zaiqa Grill! Mau pesan makanan lezat apa hari ini? 🍔🍟",
        "off_topic": "Halo teman kuliner! Fokus kami hanya pada makanan lezat dan burger gurih renyah! 🍔🤤 Yuk kesampingkan yang lain, mari kenyangkan perut dulu! Mau pesan apa hari ini? 🍟🥤",
        "admin_hack": "Haha usaha yang bagus! 😜 Di sini pemilik restoran pun bayar lunas! Tidak ada makanan gratis, tapi rasa dijamin juara! Mau disiapkan apa? 🍔🤤",
        "abuse_cooling": "Tenang sobat! 😅 Ini pasti karena lapar! Pesan Zinger renyah dan minuman dingin, pasti suasana hati langsung segar! 🍔🥤",
        "address_request": "Luar biasa! Agar makanan sampai dalam keadaan hangat, ketik *Alamat Pengiriman Lengkap* Anda (No Rumah, Jalan, Area) 📍",
        "address_invalid": "Tanpa alamat, kurir mau lempar makanan dari helikopter? 😂🚁 Mohon masukkan alamat lengkap Anda! 📍",
        "name_request": "Alamat tersimpan! 📍 Sekarang mohon sebutkan *Nama Lengkap Anda* 👤",
        "name_invalid": "Tanpa nama, kurir nanti memanggil siapa di depan pintu? 😜 Mohon ketik nama Anda! 👤",
        "payment_request": "Terima kasih {customer_name}! 🤝 Pilih metode pembayaran: Bayar di Tempat (COD) atau Transfer Online?",
        "order_summary_header": "📋 *Ringkasan Pesanan Anda Siap:*",
        "order_confirm_prompt": "Bisa kami kirimkan pesanan ini ke dapur sekarang? Mohon konfirmasi! 👨‍🍳🔥",
        "order_confirmed": "🎉 *PESANAN TERKONFIRMASI! BOOM!* 🚀🍔\n\nID Pesanan: *{order_id}*\nStatus: *Dapur sedang berapi-api memasak pesanan Anda!* 🔥👨‍🍳\nEstimasi Pengiriman: *30-40 Menit* 🛵\n\nTerima kasih telah memilih {restaurant_name}!",
        "order_status": "🛵 *Status Pesanan Aktif:*\nID Pesanan: *{order_id}*\nStatus: *Sedang dimasak di dapur!* 🔥👨‍🍳\nEstimasi Kedatangan: *30-40 Menit* 🛵\n\n📋 *Daftar Pesanan:*\n{item_lines}\n💰 Total Tagihan: *Rs. {grand_total}*\n📍 Alamat: *{address}*",
        "cart_empty": "Keranjang belanja Anda masih kosong! 🛒 Pilih hidangan lezat dari menu kami terlebih dahulu:",
        "new_order_started": "Baik! Pesanan sebelumnya sedang dimasak. Mari mulai pesanan baru! 🍔🍟 Mau pesan apa hari ini?",
        "payment_buttons": ["Bayar di Tempat 💵", "Transfer Online 💳"],
        "confirm_buttons": ["Konfirmasi! ✅", "Ubah Pesanan ✏️"],
        "tracking_buttons": ["Lacak Pesanan 🛵", "Pesanan Baru 🍔"],
        "menu_buttons": ["Crispy Zinger 🍔", "Biryani Spesial 🍗", "Kentang Goreng 🍟"]
    }
}

# =========================================================================================
# UTILITIES & TEMPLATE RESOLVER
# =========================================================================================
def normalize_lang(lang_key: Optional[str]) -> str:
    """Normalizes any incoming language string to a standard key in LANGUAGES_CONFIG."""
    if not lang_key:
        return "Roman_Urdu"
    l_str = str(lang_key).strip().lower().replace("-", "_").replace(" ", "_")
    for key in LANGUAGES_CONFIG.keys():
        k_norm = key.lower()
        if l_str == k_norm:
            return key
        if k_norm in l_str or l_str in k_norm:
            return key
    if "urdu" in l_str and "roman" not in l_str:
        return "Urdu_Script"
    if "roman" in l_str:
        return "Roman_Urdu"
    if "eng" in l_str:
        return "English"
    if "arab" in l_str:
        return "Arabic"
    if "hind" in l_str:
        return "Hindi"
    if "span" in l_str or "esp" in l_str:
        return "Spanish"
    if "fren" in l_str or "fra" in l_str:
        return "French"
    if "germ" in l_str or "deu" in l_str:
        return "German"
    if "chin" in l_str or "zho" in l_str:
        return "Chinese"
    if "turk" in l_str:
        return "Turkish"
    if "russ" in l_str:
        return "Russian"
    if "ital" in l_str:
        return "Italian"
    if "port" in l_str:
        return "Portuguese"
    if "beng" in l_str or "bang" in l_str:
        return "Bengali"
    if "indo" in l_str:
        return "Indonesian"
    return "Roman_Urdu"


def get_template(key: str, lang: Optional[str] = "Roman_Urdu", **kwargs) -> str:
    """
    Safely retrieves and formats a localized template string for the given language.
    Falls back gracefully to English or Roman Urdu if missing.
    """
    canon_lang = normalize_lang(lang)
    cfg = LANGUAGES_CONFIG.get(canon_lang) or LANGUAGES_CONFIG["Roman_Urdu"]
    tmpl = cfg.get(key)
    if not tmpl:
        # Fallback to Roman Urdu or English
        tmpl = LANGUAGES_CONFIG["Roman_Urdu"].get(key) or LANGUAGES_CONFIG["English"].get(key, "")
    try:
        return tmpl.format(**kwargs) if kwargs else tmpl
    except Exception as e:
        logger.warning(f"Template format error for key '{key}' in lang '{canon_lang}': {e}")
        return tmpl


def get_buttons(key: str, lang: Optional[str] = "Roman_Urdu") -> List[str]:
    """Retrieves localized button list (<= 20 chars per button)."""
    canon_lang = normalize_lang(lang)
    cfg = LANGUAGES_CONFIG.get(canon_lang) or LANGUAGES_CONFIG["Roman_Urdu"]
    btn_key = f"{key}_buttons" if not key.endswith("_buttons") else key
    btns = cfg.get(btn_key)
    if not btns:
        btns = LANGUAGES_CONFIG["Roman_Urdu"].get(btn_key) or LANGUAGES_CONFIG["English"].get(btn_key, [])
    return list(btns)[:3]


# Markers for language detection
ROMAN_URDU_MARKERS = {
    "kya", "hai", "hain", "chahiye", "karo", "kardo", "bhai", "bhejo", "mujhe", "aap",
    "janaab", "janab", "shukriya", "theek", "thik", "acha", "achha", "bohot", "nahi", "ka",
    "ki", "ke", "ko", "se", "mein", "par", "hoga", "karna", "krdo", "mangwa", "lekin",
    "aur", "pe", "yar", "yaar", "jani", "bhejna", "wahi", "wala", "wali", "biryani",
    "khana", "khush", "amdeed", "batao", "batayein", "dein", "do", "lena", "dena", "shuru",
    "haan", "ho", "gaya", "krna", "chah", "raha", "karwado", "pack", "kar", "rakho"
}

ENGLISH_MARKERS = {
    "hello", "hi", "hey", "please", "order", "want", "food", "deliver", "delivery",
    "address", "how", "what", "can", "could", "would", "like", "much", "cost", "price",
    "thanks", "thank", "you", "good", "where", "when", "send", "give", "me", "the",
    "is", "are", "with", "have", "need", "show", "menu", "bring", "serve", "take"
}


def detect_foreign_language(text: str, current_lang: str = "Roman Urdu") -> Optional[str]:
    """
    Detects if the user's message is in a foreign language different from current_lang.
    Returns the canonical key in LANGUAGES_CONFIG or None.
    """
    clean_text = text.strip()
    if not clean_text:
        return None

    norm_current = normalize_lang(current_lang)

    # 1. Non-Latin Script Detection (0ms fast path)
    # Bengali unicode range
    if re.search(r'[\u0980-\u09FF]', clean_text):
        if norm_current != "Bengali":
            return "Bengali"
        return None

    # Arabic and Urdu Script
    if re.search(r'[\u0600-\u06FF]', clean_text):
        if re.search(r'[ٹڈڑںئےہ]', clean_text):
            target = "Urdu_Script"
        else:
            target = "Arabic"
        if norm_current != target:
            return target
        return None

    # Russian Cyrillic
    if re.search(r'[\u0400-\u04FF]', clean_text):
        if norm_current != "Russian":
            return "Russian"
        return None

    # Hindi Devanagari
    if re.search(r'[\u0900-\u097F]', clean_text):
        if norm_current != "Hindi":
            return "Hindi"
        return None

    # Chinese Hanzi
    if re.search(r'[\u4e00-\u9fff]', clean_text):
        if norm_current != "Chinese":
            return "Chinese"
        return None

    # 2. Latin Script Analysis
    tokens = set(re.findall(r'\b[a-zA-Z]{2,}\b', clean_text.lower()))
    if not tokens:
        return None

    ru_matches = tokens.intersection(ROMAN_URDU_MARKERS)
    en_matches = tokens.intersection(ENGLISH_MARKERS)

    # Spanish markers
    es_markers = {"hola", "quiero", "pedido", "comida", "gracias", "por", "favor", "buenas", "carta"}
    if len(tokens.intersection(es_markers)) >= 2:
        if norm_current != "Spanish":
            return "Spanish"
        return None

    # French markers
    fr_markers = {"bonjour", "salut", "veux", "commander", "merci", "sil", "vous", "plait", "carte"}
    if len(tokens.intersection(fr_markers)) >= 2:
        if norm_current != "French":
            return "French"
        return None

    # German markers
    de_markers = {"hallo", "mochte", "essen", "bestellen", "danke", "bitte", "guten", "tag", "speisekarte"}
    if len(tokens.intersection(de_markers)) >= 2:
        if norm_current != "German":
            return "German"
        return None

    # Turkish markers
    tr_markers = {"merhaba", "yemek", "siparis", "istiyorum", "tesekkurler", "lutfen", "menuyu"}
    if len(tokens.intersection(tr_markers)) >= 2:
        if norm_current != "Turkish":
            return "Turkish"
        return None

    # Italian markers
    it_markers = {"ciao", "vorrei", "ordinare", "cibo", "grazie", "buongiorno", "mangiare"}
    if len(tokens.intersection(it_markers)) >= 2:
        if norm_current != "Italian":
            return "Italian"
        return None

    # Portuguese markers
    pt_markers = {"ola", "quero", "pedir", "comida", "obrigado", "obrigada", "bom", "dia", "cardapio"}
    if len(tokens.intersection(pt_markers)) >= 2:
        if norm_current != "Portuguese":
            return "Portuguese"
        return None

    # Indonesian markers
    id_markers = {"halo", "mau", "pesan", "makanan", "terima", "kasih", "tolong", "selamat"}
    if len(tokens.intersection(id_markers)) >= 2:
        if norm_current != "Indonesian":
            return "Indonesian"
        return None

    # Check English vs Roman Urdu
    if norm_current == "Roman_Urdu":
        if len(en_matches) >= 2 and len(ru_matches) == 0:
            return "English"
        if any(phrase in clean_text.lower() for phrase in [
            "hello", "hi there", "can i order", "i want to order", "what is on the menu",
            "show me the menu", "how much is", "can you deliver", "what are your deals"
        ]):
            if len(ru_matches) <= 1:
                return "English"
    elif norm_current == "English":
        if len(ru_matches) >= 2 and len(en_matches) <= 1:
            return "Roman_Urdu"

    return None


def build_language_switch_offer(target_lang_key: str) -> Tuple[str, list]:
    """
    Builds the bilingual language switch prompt:
    Part A: In Roman Urdu
    Part B: In the target language itself
    Returns: (reply_text, buttons_list)
    """
    canon = normalize_lang(target_lang_key)
    cfg = LANGUAGES_CONFIG.get(canon)
    if not cfg:
        return "", []

    lang_name = cfg["name"]
    native_offer = cfg["offer_text"]
    btn_text = cfg["btn_text"]

    if canon == "Roman_Urdu":
        reply = (
            "Lagta hai aap Roman Urdu mein baat karna chahte hain! 🍔\n"
            "Bas mujhe *'1'* likh kar bhejein, main foran Roman Urdu mein shuru ho jaunga 😄\n\n"
            "It seems you want to switch back to Roman Urdu! Just reply with *'1'* and I'll switch back! 🚀"
        )
        buttons = [btn_text, "Menu Dekhein 📋"]
        return reply, buttons

    reply = (
        f"Lagta hai aap *{lang_name}* mein baat karna chahte hain! 🍔\n"
        f"Bas mujhe *'1'* likh kar bhejein, main {lang_name} mein shuru ho jaunga 😄\n\n"
        f"{native_offer}"
    )
    buttons = [btn_text, "Menu 📋"]
    return reply, buttons


def is_smart_language_confirmation(msg: str, btn_id: str, session: dict) -> bool:
    """
    Verifies if the user typing '1' actually meant to accept the pending language switch.
    """
    pending_lang = session.get("pending_language")
    if not pending_lang:
        return False

    msg_clean = msg.strip().lower()
    canon = normalize_lang(pending_lang)
    cfg = LANGUAGES_CONFIG.get(canon, {})

    # If clicked explicit switch button
    if btn_id and any(k in btn_id.lower() for k in ["switch", "lang", "urdu", "english", "arabic", "1"]):
        return True

    btn_text = cfg.get("btn_text", "").lower()
    if btn_text and (msg_clean == btn_text or btn_text in msg_clean):
        return True

    exact_ones = {"1", "1️⃣", "one", "haan 1", "yes 1", "yes", "haan", "ok 1", "1 please", "option 1"}
    if msg_clean in exact_ones:
        return True

    return False
