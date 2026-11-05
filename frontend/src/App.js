/* eslint-disable */
import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShoppingBag,
  Send,
  RotateCcw,
  Check,
  CheckCircle2,
  MapPin,
  Clock,
  Plus,
  Minus,
  Trash2,
  ArrowRight,
  ChevronRight,
  Sun,
  Moon,
  MessageSquare,
  UtensilsCrossed,
  CreditCard,
  Truck,
  Sparkles,
  Phone,
  User,
  ArrowLeft,
  Share2,
  ReceiptText
} from 'lucide-react';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const DEFAULT_PHONE = '+923001112233';

// Curated luxury menu catalog with real photography
const MENU_CATALOG = [
  {
    id: "zinger",
    name: "Crispy Zinger Burger",
    category: "Burgers",
    image: "/images/zinger.jpg",
    description: "Crispy fried golden chicken fillet oozing with cheddar lava cheese sauce in a freshly toasted brioche bun.",
    basePrice: 550,
    badge: "Bestseller 🔥",
    variants: [
      { name: "Regular", price: 550 },
      { name: "Cheese Lava", price: 650 }
    ]
  },
  {
    id: "biryani",
    name: "Special Chicken Biryani",
    category: "Rice",
    image: "/images/biryani.jpg",
    description: "Royal fragrant long-grain basmati rice cooked in artisanal clay pot with tender spices and chicken leg.",
    basePrice: 400,
    badge: "Chef Special 👑",
    variants: [
      { name: "Single Mild", price: 400 },
      { name: "Single Spicy", price: 400 },
      { name: "Double Mild", price: 750 },
      { name: "Double Spicy", price: 750 }
    ]
  },
  {
    id: "fries",
    name: "Loaded Fries",
    category: "Sides",
    image: "/images/fries.jpg",
    description: "Golden potato french fries layered with bubbling melted cheese, garlic mayo, and spicy jalapeno slices.",
    basePrice: 450,
    badge: "Crispy 🧀",
    variants: [
      { name: "Mayo Garlic", price: 450 },
      { name: "Jalapeno Cheese", price: 450 }
    ]
  },
  {
    id: "margarita",
    name: "Mint Margarita",
    category: "Drinks",
    image: "/images/margarita.jpg",
    description: "Chilled electric mint cooler with fresh crushed garden mint leaves, ice crystals, and lime wheel garnish.",
    basePrice: 150,
    badge: "Chilled ❄️",
    variants: [
      { name: "Regular", price: 150 }
    ]
  }
];

export default function App() {
  // Theme state: default is PREMIUM WHITE (isDark = false)
  const [isDark, setIsDark] = useState(() => {
    return localStorage.getItem('theme_mode') === 'dark';
  });

  // Navigation pages: 'menu' | 'chat' | 'cart' | 'checkout' | 'success'
  const [activePage, setActivePage] = useState('menu');

  // Menu category filter
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [menuCatalog, setMenuCatalog] = useState(MENU_CATALOG);

  // Fetch live menu dynamically from backend
  useEffect(() => {
    fetch(`${API_URL}/menu`)
      .then(res => res.json())
      .then(data => {
        if (data && data.items && data.items.length > 0) {
          setMenuCatalog(data.items);
        }
      })
      .catch(err => console.log('Using default menu catalog fallback:', err));
  }, []);

  // Cart state: items array
  const [cartItems, setCartItems] = useState([
    {
      id: 'zinger',
      name: 'Crispy Zinger Burger',
      variant: 'Cheese Lava',
      price: 650,
      qty: 1,
      image: '/images/zinger.jpg'
    }
  ]);

  // Selected variants for each menu card
  const [selectedVariants, setSelectedVariants] = useState({
    zinger: 'Cheese Lava',
    biryani: 'Single Spicy',
    fries: 'Mayo Garlic',
    margarita: 'Regular'
  });

  // Customer Checkout Details
  const [customerDetails, setCustomerDetails] = useState({
    name: 'Saqiq Shahzad',
    phone: DEFAULT_PHONE,
    address: 'House #42, Street 7, Phase 5, DHA, Karachi',
    notes: 'Please bring hot and crispy. Ring bell twice.',
    paymentMethod: 'Cash on Delivery (COD)'
  });

  // Confirmed Order Data (for Dopamine Success Page)
  const [confirmedOrder, setConfirmedOrder] = useState(null);

  // Chat conversation state
  const [chatMessages, setChatMessages] = useState([
    {
      id: 1,
      role: 'ai',
      text: "Assalam-o-Alaikum! **Zaiqa Grill & Fast Food** mein khush amdeed 🍔🍕\n\nAap yahan direct food order kar sakte hain. Bataiye aaj kya khana pasand karein ge?",
      buttons: ["Crispy Zinger 🍔", "Special Biryani 🍗", "Loaded Fries 🍟", "Cart Dekhao 🛒"],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isAiTyping, setIsAiTyping] = useState(false);

  // Toast notification
  const [toastText, setToastText] = useState(null);

  // Countdown timer for confirmed order
  const [countdownSeconds, setCountdownSeconds] = useState(35 * 60);

  const chatEndRef = useRef(null);

  // Handle Theme Switcher
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme_mode', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme_mode', 'light');
    }
  }, [isDark]);

  // Scroll chat to bottom
  useEffect(() => {
    if (activePage === 'chat') {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, isAiTyping, activePage]);

  // Countdown ticker for order success
  useEffect(() => {
    if (activePage === 'success' && countdownSeconds > 0) {
      const timer = setInterval(() => {
        setCountdownSeconds(prev => Math.max(0, prev - 1));
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [activePage, countdownSeconds]);

  // Toast trigger
  const showToast = (text) => {
    setToastText(text);
    setTimeout(() => setToastText(null), 3000);
  };

  // Cart Calculations
  const subtotal = cartItems.reduce((sum, item) => sum + (item.price * item.qty), 0);
  const deliveryFee = cartItems.length > 0 ? 150 : 0;
  const grandTotal = subtotal + deliveryFee;
  const totalItemCount = cartItems.reduce((sum, item) => sum + item.qty, 0);

  // Add Item to Cart
  const handleAddToCart = (product) => {
    const variantName = selectedVariants[product.id] || product.variants[0].name;
    const variantObj = product.variants.find(v => v.name === variantName) || product.variants[0];
    const price = variantObj.price;

    setCartItems(prev => {
      const existingIdx = prev.findIndex(item => item.id === product.id && item.variant === variantName);
      if (existingIdx > -1) {
        const copy = [...prev];
        copy[existingIdx].qty += 1;
        return copy;
      }
      return [
        ...prev,
        {
          id: product.id,
          name: product.name,
          variant: variantName,
          price: price,
          qty: 1,
          image: product.image
        }
      ];
    });

    showToast(`Added ${product.name} (${variantName}) to cart! 🛒`);
  };

  // Change Item Quantity
  const handleUpdateQty = (idx, delta) => {
    setCartItems(prev => {
      const copy = [...prev];
      const newQty = copy[idx].qty + delta;
      if (newQty <= 0) {
        return copy.filter((_, i) => i !== idx);
      }
      copy[idx].qty = newQty;
      return copy;
    });
  };

  // Remove Item
  const handleRemoveItem = (idx) => {
    setCartItems(prev => prev.filter((_, i) => i !== idx));
    showToast("Item removed from cart");
  };

  // Clear Entire Cart
  const handleClearCart = () => {
    if (window.confirm("Do you want to clear your cart?")) {
      setCartItems([]);
      showToast("Cart cleared");
    }
  };

  // Send Message to AI Assistant
  const handleSendChatMessage = async (textToSend, buttonId = null) => {
    const text = (textToSend || chatInput).trim();
    if (!text && !buttonId) return;

    const userMsg = {
      id: Date.now(),
      role: 'user',
      text: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setChatMessages(prev => [...prev, userMsg]);
    setChatInput('');
    setIsAiTyping(true);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          phone: DEFAULT_PHONE,
          btn_id: buttonId,
          restaurant_id: 'default_restaurant'
        })
      });

      if (!res.ok) throw new Error("Server error");
      const data = await res.json();

      const reply = data.reply_text || data.response || "Order noted!";
      const buttons = data.buttons || [];

      // If backend updated cart, sync it
      if (data.cart && data.cart.items && data.cart.items.length > 0) {
        const synced = data.cart.items.map(it => ({
          id: it.name.toLowerCase().includes('burger') ? 'zinger' : it.name.toLowerCase().includes('biryani') ? 'biryani' : 'fries',
          name: it.name,
          variant: it.variant || 'Regular',
          price: it.unit_price,
          qty: it.qty,
          image: it.name.toLowerCase().includes('burger') ? '/images/zinger.jpg' : it.name.toLowerCase().includes('biryani') ? '/images/biryani.jpg' : '/images/fries.jpg'
        }));
        setCartItems(synced);
      }

      setChatMessages(prev => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'ai',
          text: reply,
          buttons: buttons,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } catch (e) {
      setChatMessages(prev => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'ai',
          text: "Server connection failed. Baraye meharbani backend check karein.",
          buttons: ["Retry"],
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setIsAiTyping(false);
    }
  };

  // Place Order from Checkout Form
  const handlePlaceOrder = () => {
    if (!customerDetails.name.trim() || !customerDetails.address.trim()) {
      alert("Please provide your Name and Complete Delivery Address.");
      return;
    }

    if (cartItems.length === 0) {
      alert("Your cart is empty. Please add items before placing order.");
      return;
    }

    const orderRef = `ZG-${Math.floor(100000 + Math.random() * 900000)}`;
    const newOrder = {
      orderId: orderRef,
      date: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      items: [...cartItems],
      subtotal,
      deliveryFee,
      grandTotal,
      customer: { ...customerDetails }
    };

    setConfirmedOrder(newOrder);
    setCountdownSeconds(35 * 60);
    setActivePage('success');
  };

  const categories = ['All', 'Burgers', 'Rice', 'Sides', 'Drinks'];
  const filteredProducts = selectedCategory === 'All'
    ? menuCatalog
    : menuCatalog.filter(item => {
        const cat = item.category || '';
        return cat.toLowerCase().includes(selectedCategory.toLowerCase());
      });

  // Format timer
  const formatTimer = (sec) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className={`min-h-screen flex flex-col transition-colors duration-300 ${
      isDark ? 'bg-[#070709] text-zinc-100' : 'bg-[#fafafa] text-zinc-900'
    }`}>

      {/* --- 🌟 TOP NAVIGATION BAR --- */}
      <header className={`sticky top-0 z-40 border-b transition-colors duration-300 ${
        isDark ? 'bg-[#09090c]/90 border-zinc-800/80 frosted-glass' : 'bg-white/90 border-zinc-200/80 frosted-glass'
      }`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-8 h-20 flex items-center justify-between gap-4">
          
          {/* Logo Brand */}
          <div
            onClick={() => setActivePage('menu')}
            className="flex items-center gap-3 cursor-pointer select-none group"
          >
            <div className={`w-11 h-11 rounded-2xl flex items-center justify-center font-heading font-black text-xl transition-all shadow-sm ${
              isDark ? 'bg-white text-black' : 'bg-zinc-900 text-white'
            }`}>
              Z
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-heading font-black text-lg tracking-tight uppercase">
                  Zaiqa Grill
                </span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                  Live
                </span>
              </div>
              <p className="text-xs text-zinc-400 font-medium">Fast Food & AI Ordering</p>
            </div>
          </div>

          {/* Desktop Navigation Pages */}
          <nav className="hidden md:flex items-center gap-1.5 p-1 rounded-2xl border transition-colors ${
            isDark ? 'bg-zinc-900/60 border-zinc-800' : 'bg-zinc-100/70 border-zinc-200'
          }">
            <button
              onClick={() => setActivePage('menu')}
              className={`px-5 py-2.5 rounded-xl font-heading text-xs font-bold tracking-wide transition-all flex items-center gap-2 ${
                activePage === 'menu'
                  ? isDark ? 'bg-white text-zinc-900 shadow-sm' : 'bg-zinc-900 text-white shadow-sm'
                  : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'
              }`}
            >
              <UtensilsCrossed className="w-3.5 h-3.5" />
              Menu
            </button>

            <button
              onClick={() => setActivePage('chat')}
              className={`px-5 py-2.5 rounded-xl font-heading text-xs font-bold tracking-wide transition-all flex items-center gap-2 ${
                activePage === 'chat'
                  ? isDark ? 'bg-white text-zinc-900 shadow-sm' : 'bg-zinc-900 text-white shadow-sm'
                  : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              AI Assistant
            </button>

            <button
              onClick={() => setActivePage('cart')}
              className={`px-5 py-2.5 rounded-xl font-heading text-xs font-bold tracking-wide transition-all flex items-center gap-2 relative ${
                activePage === 'cart'
                  ? isDark ? 'bg-white text-zinc-900 shadow-sm' : 'bg-zinc-900 text-white shadow-sm'
                  : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'
              }`}
            >
              <ShoppingBag className="w-3.5 h-3.5" />
              Cart
              {totalItemCount > 0 && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-emerald-500 text-white">
                  {totalItemCount}
                </span>
              )}
            </button>

            <button
              onClick={() => setActivePage('checkout')}
              className={`px-5 py-2.5 rounded-xl font-heading text-xs font-bold tracking-wide transition-all flex items-center gap-2 ${
                activePage === 'checkout'
                  ? isDark ? 'bg-white text-zinc-900 shadow-sm' : 'bg-zinc-900 text-white shadow-sm'
                  : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'
              }`}
            >
              <CreditCard className="w-3.5 h-3.5" />
              Checkout
            </button>
          </nav>

          {/* Right Actions: Premium Glassmorphic Theme Toggle */}
          <div className="flex items-center gap-3">
            {/* Cart Quick Button (Mobile & Desktop) */}
            <button
              onClick={() => setActivePage('cart')}
              className={`p-2.5 rounded-xl border flex items-center gap-2 transition-all ${
                isDark
                  ? 'bg-zinc-900 border-zinc-800 hover:border-zinc-700 text-zinc-200'
                  : 'bg-white border-zinc-200 hover:border-zinc-300 text-zinc-800'
              }`}
            >
              <ShoppingBag className="w-4 h-4" />
              <span className="font-heading text-xs font-bold">
                {totalItemCount}
              </span>
            </button>

            {/* ✨ PREMIUM BLUR GLASS TOGGLE (Sun / Moon) */}
            <div className={`p-1 rounded-full border flex items-center gap-1 shadow-sm transition-all ${
              isDark
                ? 'bg-zinc-900/80 border-zinc-700/80 frosted-glass'
                : 'bg-white/80 border-zinc-300/80 frosted-glass'
            }`}>
              <button
                onClick={() => setIsDark(false)}
                title="Light Mode"
                className={`p-1.5 rounded-full transition-all ${
                  !isDark
                    ? 'bg-zinc-900 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <Sun className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setIsDark(true)}
                title="Dark Mode"
                className={`p-1.5 rounded-full transition-all ${
                  isDark
                    ? 'bg-white text-zinc-900 shadow-sm'
                    : 'text-zinc-500 hover:text-zinc-800'
                }`}
              >
                <Moon className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Sub-Navigation Bar */}
        <div className={`flex md:hidden border-t overflow-x-auto no-scrollbar transition-colors ${
          isDark ? 'bg-[#09090c] border-zinc-800' : 'bg-white border-zinc-200'
        }`}>
          {[
            { id: 'menu', label: 'Menu', icon: UtensilsCrossed },
            { id: 'chat', label: 'AI Bot', icon: MessageSquare },
            { id: 'cart', label: `Cart (${totalItemCount})`, icon: ShoppingBag },
            { id: 'checkout', label: 'Checkout', icon: CreditCard }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActivePage(tab.id)}
              className={`flex-1 py-3 px-2 text-xs font-heading font-bold text-center flex items-center justify-center gap-1.5 shrink-0 ${
                activePage === tab.id
                  ? isDark ? 'text-white border-b-2 border-white' : 'text-zinc-900 border-b-2 border-zinc-900'
                  : 'text-zinc-400'
              }`}
            >
              <tab.icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          ))}
        </div>
      </header>

      {/* --- 🍱 MAIN APPLICATION WORKSPACE --- */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-8">
        
        {/* ========================================================================= */}
        {/* PAGE 1: MENU (ALAG PAGE)                                                  */}
        {/* ========================================================================= */}
        {activePage === 'menu' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-8"
          >
            {/* Page Header */}
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b pb-6 transition-colors dark:border-zinc-800 border-zinc-200">
              <div>
                <span className="text-xs uppercase font-extrabold tracking-widest text-emerald-600 dark:text-emerald-400 font-mono">
                  Authentic Karachi Flavours
                </span>
                <h1 className="font-heading font-black text-3xl sm:text-4xl tracking-tight mt-1">
                  Our Food Menu
                </h1>
                <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
                  Crispy Zingers, Saffron Biryani, Loaded Fries aur Refreshing Coolers.
                </p>
              </div>

              {/* Category Pills */}
              <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-1">
                {categories.map(cat => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-4 py-2 rounded-xl text-xs font-heading font-bold transition-all shrink-0 ${
                      selectedCategory === cat
                        ? isDark ? 'bg-white text-zinc-900 shadow-sm' : 'bg-zinc-900 text-white shadow-sm'
                        : isDark ? 'bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800' : 'bg-zinc-100 text-zinc-600 hover:text-zinc-900 border border-zinc-200'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            {/* Menu Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {filteredProducts.map((prod) => {
                const currentVariant = selectedVariants[prod.id] || prod.variants[0].name;
                const currentPrice = prod.variants.find(v => v.name === currentVariant)?.price || prod.basePrice;

                return (
                  <div
                    key={prod.id}
                    className={`rounded-3xl overflow-hidden border flex flex-col justify-between transition-all duration-300 group hover:-translate-y-1 ${
                      isDark
                        ? 'bg-[#0b0b0f] border-zinc-800/80 hover:border-zinc-700 shadow-dark-card hover:shadow-dark-hover'
                        : 'bg-white border-zinc-200/90 hover:border-zinc-300 shadow-clean hover:shadow-clean-hover'
                    }`}
                  >
                    {/* Image Thumbnail */}
                    <div className="relative h-56 w-full overflow-hidden bg-zinc-950">
                      <img
                        src={prod.image}
                        alt={prod.name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        onError={(e) => { e.target.src = "/images/zinger.jpg"; }}
                      />
                      <span className="absolute top-3 left-3 px-3 py-1 rounded-full text-xs font-heading font-bold bg-white/90 dark:bg-black/80 backdrop-blur-md shadow-sm">
                        {prod.badge}
                      </span>
                      <span className={`absolute bottom-3 right-3 font-mono font-bold text-sm px-3 py-1 rounded-xl shadow-sm ${
                        isDark ? 'bg-white text-zinc-950' : 'bg-zinc-950 text-white'
                      }`}>
                        PKR {currentPrice}
                      </span>
                    </div>

                    {/* Card Content */}
                    <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
                      <div>
                        <h3 className="font-heading font-bold text-lg tracking-tight">
                          {prod.name}
                        </h3>
                        <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 line-clamp-2 leading-relaxed">
                          {prod.description}
                        </p>
                      </div>

                      {/* Variant Selector */}
                      <div className="space-y-2">
                        <span className="text-[10px] font-mono uppercase tracking-wider font-bold text-zinc-400">
                          Select Variant:
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {prod.variants.map((v) => (
                            <button
                              key={v.name}
                              onClick={() => setSelectedVariants(prev => ({ ...prev, [prod.id]: v.name }))}
                              className={`px-2.5 py-1 rounded-lg text-xs font-heading font-bold transition-all ${
                                currentVariant === v.name
                                  ? isDark ? 'bg-zinc-200 text-zinc-900 shadow-sm' : 'bg-zinc-900 text-white shadow-sm'
                                  : isDark ? 'bg-zinc-900 text-zinc-400 border border-zinc-800' : 'bg-zinc-100 text-zinc-600 border border-zinc-200'
                              }`}
                            >
                              {v.name}
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Add Button */}
                      <button
                        onClick={() => handleAddToCart(prod)}
                        className={`w-full py-3.5 rounded-2xl font-heading font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all active:scale-98 ${
                          isDark
                            ? 'bg-white text-zinc-950 hover:bg-zinc-200'
                            : 'bg-zinc-900 text-white hover:bg-zinc-800'
                        }`}
                      >
                        <Plus className="w-4 h-4" />
                        Add to Cart
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Bottom Floating Bar when items in cart */}
            {cartItems.length > 0 && (
              <div className={`p-4 rounded-2xl border flex flex-col sm:flex-row items-center justify-between gap-4 shadow-clean transition-colors ${
                isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'
              }`}>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center font-bold">
                    <ShoppingBag className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-heading font-bold text-sm">
                      {totalItemCount} Items Added in Cart
                    </h4>
                    <p className="text-xs text-zinc-400">Total: <span className="font-bold text-emerald-500 font-mono">PKR {grandTotal}</span> (Incl. Delivery)</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 w-full sm:w-auto">
                  <button
                    onClick={() => setActivePage('cart')}
                    className={`flex-1 sm:flex-initial px-6 py-3 rounded-xl font-heading font-bold text-xs uppercase tracking-wider border transition-colors ${
                      isDark ? 'border-zinc-700 hover:bg-zinc-800 text-white' : 'border-zinc-300 hover:bg-zinc-100 text-zinc-900'
                    }`}
                  >
                    View Cart
                  </button>
                  <button
                    onClick={() => setActivePage('checkout')}
                    className="flex-1 sm:flex-initial px-6 py-3 rounded-xl font-heading font-bold text-xs uppercase tracking-wider bg-emerald-500 hover:bg-emerald-600 text-white shadow-sm flex items-center justify-center gap-2"
                  >
                    <span>Checkout</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* ========================================================================= */}
        {/* PAGE 2: AI CONCIERGE CHAT (ALAG PAGE)                                     */}
        {/* ========================================================================= */}
        {activePage === 'chat' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`max-w-4xl mx-auto h-[740px] rounded-3xl border flex flex-col overflow-hidden shadow-clean transition-colors ${
              isDark ? 'bg-[#09090c] border-zinc-800' : 'bg-white border-zinc-200'
            }`}
          >
            {/* Chat Top Banner */}
            <div className={`p-4 sm:px-6 border-b flex items-center justify-between transition-colors ${
              isDark ? 'bg-zinc-900/60 border-zinc-800' : 'bg-zinc-50 border-zinc-200'
            }`}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center font-bold">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-heading font-bold text-sm tracking-tight">
                    AI Order Assistant
                  </h3>
                  <p className="text-xs text-zinc-400 flex items-center gap-1.5 font-mono">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    WhatsApp Multi-Tier LLM Online
                  </p>
                </div>
              </div>

              <button
                onClick={() => setActivePage('cart')}
                className={`text-xs font-heading font-bold px-3 py-1.5 rounded-xl border flex items-center gap-1.5 ${
                  isDark ? 'border-zinc-800 bg-zinc-900 text-zinc-300' : 'border-zinc-200 bg-white text-zinc-700'
                }`}
              >
                <ShoppingBag className="w-3.5 h-3.5" />
                Cart ({totalItemCount})
              </button>
            </div>

            {/* Chat Messages Stream */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
              {chatMessages.map(msg => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-[85%] sm:max-w-[75%] p-4 rounded-2xl text-sm leading-relaxed ${
                      msg.role === 'user'
                        ? isDark ? 'bg-white text-zinc-950 font-medium rounded-br-none' : 'bg-zinc-900 text-white font-medium rounded-br-none'
                        : isDark ? 'bg-zinc-900/90 text-zinc-100 border border-zinc-800 rounded-bl-none' : 'bg-zinc-100 text-zinc-900 border border-zinc-200/80 rounded-bl-none'
                    }`}
                  >
                    <div className="chat-markdown">
                      <ReactMarkdown>{msg.text}</ReactMarkdown>
                    </div>
                    <div className={`text-[10px] mt-2 font-mono flex items-center gap-1 ${
                      msg.role === 'user'
                        ? isDark ? 'text-zinc-600 justify-end' : 'text-zinc-400 justify-end'
                        : 'text-zinc-400 justify-start'
                    }`}>
                      <Clock className="w-2.5 h-2.5" />
                      <span>{msg.timestamp}</span>
                    </div>
                  </div>

                  {/* Buttons if provided by bot */}
                  {msg.buttons && msg.buttons.length > 0 && (
                    <div className="mt-2.5 flex flex-wrap gap-2">
                      {msg.buttons.map((btn, bIdx) => (
                        <button
                          key={bIdx}
                          onClick={() => handleSendChatMessage(btn, `btn_${bIdx + 1}`)}
                          className={`px-3 py-1.5 rounded-xl text-xs font-heading font-bold border transition-all ${
                            isDark
                              ? 'bg-zinc-900 border-zinc-800 hover:border-zinc-600 text-zinc-200'
                              : 'bg-white border-zinc-300 hover:border-zinc-400 text-zinc-800'
                          }`}
                        >
                          {btn}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}

              {isAiTyping && (
                <div className="flex items-center gap-2 p-3 rounded-xl bg-zinc-100 dark:bg-zinc-900 border dark:border-zinc-800 border-zinc-200 w-fit">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
                  <span className="text-xs font-mono text-zinc-400">AI Bot is typing...</span>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Quick Chips Bar */}
            <div className={`px-4 py-2 border-t flex items-center gap-2 overflow-x-auto no-scrollbar ${
              isDark ? 'bg-zinc-900/40 border-zinc-800' : 'bg-zinc-50 border-zinc-200'
            }`}>
              <span className="text-[10px] uppercase font-bold text-zinc-400 font-mono">QUICK:</span>
              {["Menu Dikhao 📋", "2 Crispy Zinger 🍔", "Loaded Fries 🍟", "Cart Dekhao 🛒", "Checkout 💳"].map((chip, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendChatMessage(chip)}
                  className={`shrink-0 px-3 py-1 rounded-lg text-xs font-heading font-semibold border ${
                    isDark ? 'bg-zinc-900 border-zinc-800 text-zinc-300 hover:text-white' : 'bg-white border-zinc-200 text-zinc-700 hover:text-black'
                  }`}
                >
                  {chip}
                </button>
              ))}
            </div>

            {/* Input Dock */}
            <div className={`p-4 border-t ${isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'}`}>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendChatMessage();
                }}
                className="flex items-center gap-2"
              >
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Kuch bhi likhein... (e.g. 1 Special Biryani Spicy chahiye)"
                  className={`flex-1 px-4 py-3.5 rounded-2xl border text-sm font-sans focus:outline-none transition-all ${
                    isDark
                      ? 'bg-zinc-950 border-zinc-800 text-white placeholder-zinc-500 focus:border-zinc-600'
                      : 'bg-zinc-50 border-zinc-300 text-zinc-900 placeholder-zinc-400 focus:border-zinc-400'
                  }`}
                />
                <button
                  type="submit"
                  disabled={isAiTyping || !chatInput.trim()}
                  className={`p-3.5 rounded-2xl transition-all ${
                    chatInput.trim()
                      ? isDark ? 'bg-white text-zinc-950 font-bold' : 'bg-zinc-900 text-white font-bold'
                      : 'bg-zinc-200 dark:bg-zinc-800 text-zinc-400 cursor-not-allowed'
                  }`}
                >
                  <Send className="w-5 h-5" />
                </button>
              </form>
            </div>
          </motion.div>
        )}

        {/* ========================================================================= */}
        {/* PAGE 3: CART (ALAG PAGE)                                                  */}
        {/* ========================================================================= */}
        {activePage === 'cart' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="max-w-4xl mx-auto space-y-6"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b pb-4 dark:border-zinc-800 border-zinc-200">
              <div>
                <h1 className="font-heading font-black text-3xl tracking-tight">
                  Your Food Cart
                </h1>
                <p className="text-sm text-zinc-400 mt-1">Review items before proceeding to checkout</p>
              </div>

              {cartItems.length > 0 && (
                <button
                  onClick={handleClearCart}
                  className="text-xs font-heading font-bold text-red-500 hover:text-red-600 flex items-center gap-1.5"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Clear Cart
                </button>
              )}
            </div>

            {cartItems.length === 0 ? (
              <div className={`p-12 rounded-3xl border text-center space-y-4 ${
                isDark ? 'bg-zinc-900/50 border-zinc-800' : 'bg-white border-zinc-200'
              }`}>
                <div className="w-16 h-16 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center mx-auto text-zinc-400">
                  <ShoppingBag className="w-8 h-8" />
                </div>
                <h3 className="font-heading font-bold text-xl">Your cart is currently empty</h3>
                <p className="text-sm text-zinc-400 max-w-sm mx-auto">
                  Looks like you haven't added anything to your cart yet. Explore our delicious burgers and biryani!
                </p>
                <button
                  onClick={() => setActivePage('menu')}
                  className={`px-6 py-3 rounded-xl font-heading font-bold text-xs uppercase tracking-wider ${
                    isDark ? 'bg-white text-zinc-950' : 'bg-zinc-900 text-white'
                  }`}
                >
                  Explore Food Menu ➔
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                
                {/* Items List (7 cols) */}
                <div className="lg:col-span-7 space-y-3">
                  {cartItems.map((item, idx) => (
                    <div
                      key={idx}
                      className={`p-4 rounded-2xl border flex items-center justify-between gap-4 transition-colors ${
                        isDark ? 'bg-zinc-900/60 border-zinc-800' : 'bg-white border-zinc-200 shadow-sm'
                      }`}
                    >
                      {/* Thumbnail & Info */}
                      <div className="flex items-center gap-3.5">
                        <img
                          src={item.image}
                          alt={item.name}
                          className="w-16 h-16 rounded-xl object-cover bg-black"
                          onError={(e) => { e.target.src = "/images/zinger.jpg"; }}
                        />
                        <div>
                          <h4 className="font-heading font-bold text-sm">
                            {item.name}
                          </h4>
                          <span className="text-xs font-mono text-zinc-400">
                            {item.variant} • PKR {item.price} each
                          </span>
                        </div>
                      </div>

                      {/* Controls */}
                      <div className="flex items-center gap-4">
                        <div className={`flex items-center border rounded-xl p-1 ${
                          isDark ? 'border-zinc-700 bg-zinc-950' : 'border-zinc-300 bg-zinc-50'
                        }`}>
                          <button
                            onClick={() => handleUpdateQty(idx, -1)}
                            className="p-1 hover:bg-zinc-200 dark:hover:bg-zinc-800 rounded-lg transition-colors"
                          >
                            <Minus className="w-3.5 h-3.5" />
                          </button>
                          <span className="font-mono text-xs font-bold px-2.5">
                            {item.qty}
                          </span>
                          <button
                            onClick={() => handleUpdateQty(idx, 1)}
                            className="p-1 hover:bg-zinc-200 dark:hover:bg-zinc-800 rounded-lg transition-colors"
                          >
                            <Plus className="w-3.5 h-3.5" />
                          </button>
                        </div>

                        <div className="text-right min-w-[70px]">
                          <span className="font-mono font-bold text-sm">
                            PKR {item.price * item.qty}
                          </span>
                        </div>

                        <button
                          onClick={() => handleRemoveItem(idx)}
                          className="text-zinc-400 hover:text-red-500 transition-colors p-1"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Bill Summary (5 cols) */}
                <div className={`lg:col-span-5 p-6 rounded-3xl border space-y-4 ${
                  isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200 shadow-clean'
                }`}>
                  <h3 className="font-heading font-bold text-lg border-b pb-3 dark:border-zinc-800 border-zinc-200">
                    Order Summary
                  </h3>

                  <div className="space-y-2 text-xs font-mono text-zinc-500 dark:text-zinc-400">
                    <div className="flex justify-between">
                      <span>Subtotal ({totalItemCount} items):</span>
                      <span className="text-zinc-900 dark:text-zinc-100 font-bold">PKR {subtotal}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="flex items-center gap-1">
                        <Truck className="w-3.5 h-3.5" />
                        Flat Delivery Fee:
                      </span>
                      <span className="text-zinc-900 dark:text-zinc-100 font-bold">PKR {deliveryFee}</span>
                    </div>
                    <div className="flex justify-between pt-3 border-t text-sm font-bold dark:border-zinc-800 border-zinc-200">
                      <span className="text-zinc-900 dark:text-white font-heading">GRAND TOTAL:</span>
                      <span className="text-emerald-500 font-mono text-base font-extrabold">
                        PKR {grandTotal}
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={() => setActivePage('checkout')}
                    className={`w-full py-4 rounded-2xl font-heading font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-sm transition-all ${
                      isDark ? 'bg-white text-zinc-950 hover:bg-zinc-200' : 'bg-zinc-900 text-white hover:bg-zinc-800'
                    }`}
                  >
                    <span>Proceed to Checkout</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>

                  <button
                    onClick={() => setActivePage('menu')}
                    className="w-full text-center text-xs font-heading font-bold text-zinc-400 hover:text-zinc-900 dark:hover:text-white"
                  >
                    + Add More Items
                  </button>
                </div>

              </div>
            )}
          </motion.div>
        )}

        {/* ========================================================================= */}
        {/* PAGE 4: CHECKOUT & DELIVERY DETAILS (ALAG PAGE)                           */}
        {/* ========================================================================= */}
        {activePage === 'checkout' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="max-w-4xl mx-auto space-y-6"
          >
            {/* Header */}
            <div className="flex items-center gap-3 border-b pb-4 dark:border-zinc-800 border-zinc-200">
              <button
                onClick={() => setActivePage('cart')}
                className="p-2 rounded-xl border dark:border-zinc-800 border-zinc-200 text-zinc-400 hover:text-zinc-900 dark:hover:text-white"
              >
                <ArrowLeft className="w-4 h-4" />
              </button>
              <div>
                <h1 className="font-heading font-black text-3xl tracking-tight">
                  Checkout & Delivery Details
                </h1>
                <p className="text-sm text-zinc-400">Fill in your delivery address to confirm the order</p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
              
              {/* Form Details (7 cols) */}
              <div className={`lg:col-span-7 p-6 rounded-3xl border space-y-5 ${
                isDark ? 'bg-zinc-900/60 border-zinc-800' : 'bg-white border-zinc-200 shadow-clean'
              }`}>
                <h3 className="font-heading font-bold text-base flex items-center gap-2">
                  <User className="w-4 h-4 text-emerald-500" />
                  Customer Information
                </h3>

                <div className="space-y-4 text-xs font-heading">
                  <div>
                    <label className="block font-bold text-zinc-500 uppercase tracking-wider mb-1.5 font-mono text-[10px]">
                      Full Name *
                    </label>
                    <input
                      type="text"
                      value={customerDetails.name}
                      onChange={(e) => setCustomerDetails(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="e.g. Saqiq Shahzad"
                      className={`w-full p-3.5 rounded-xl border text-sm font-sans focus:outline-none transition-colors ${
                        isDark ? 'bg-zinc-950 border-zinc-800 text-white focus:border-zinc-600' : 'bg-zinc-50 border-zinc-300 text-zinc-900 focus:border-zinc-400'
                      }`}
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-zinc-500 uppercase tracking-wider mb-1.5 font-mono text-[10px]">
                      WhatsApp Contact Number *
                    </label>
                    <input
                      type="text"
                      value={customerDetails.phone}
                      onChange={(e) => setCustomerDetails(prev => ({ ...prev, phone: e.target.value }))}
                      placeholder="+92 300 1234567"
                      className={`w-full p-3.5 rounded-xl border text-sm font-sans focus:outline-none transition-colors ${
                        isDark ? 'bg-zinc-950 border-zinc-800 text-white focus:border-zinc-600' : 'bg-zinc-50 border-zinc-300 text-zinc-900 focus:border-zinc-400'
                      }`}
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-zinc-500 uppercase tracking-wider mb-1.5 font-mono text-[10px]">
                      Complete Delivery Address & Landmark *
                    </label>
                    <textarea
                      rows={3}
                      value={customerDetails.address}
                      onChange={(e) => setCustomerDetails(prev => ({ ...prev, address: e.target.value }))}
                      placeholder="House / Apartment number, Street name, Phase/Area, City"
                      className={`w-full p-3.5 rounded-xl border text-sm font-sans focus:outline-none transition-colors resize-none ${
                        isDark ? 'bg-zinc-950 border-zinc-800 text-white focus:border-zinc-600' : 'bg-zinc-50 border-zinc-300 text-zinc-900 focus:border-zinc-400'
                      }`}
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-zinc-500 uppercase tracking-wider mb-1.5 font-mono text-[10px]">
                      Order Notes / Instructions (Optional)
                    </label>
                    <input
                      type="text"
                      value={customerDetails.notes}
                      onChange={(e) => setCustomerDetails(prev => ({ ...prev, notes: e.target.value }))}
                      placeholder="e.g. less spicy, extra sauce, call on arrival"
                      className={`w-full p-3.5 rounded-xl border text-sm font-sans focus:outline-none transition-colors ${
                        isDark ? 'bg-zinc-950 border-zinc-800 text-white focus:border-zinc-600' : 'bg-zinc-50 border-zinc-300 text-zinc-900 focus:border-zinc-400'
                      }`}
                    />
                  </div>

                  {/* Payment Method Selection */}
                  <div className="pt-2">
                    <label className="block font-bold text-zinc-500 uppercase tracking-wider mb-2 font-mono text-[10px]">
                      Select Payment Method
                    </label>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                      {[
                        { id: 'Cash on Delivery (COD)', label: 'Cash on Delivery 💵' },
                        { id: 'Online Transfer', label: 'Online Bank / Easypaisa 📱' },
                        { id: 'Card on Delivery', label: 'Card on Delivery 💳' }
                      ].map((method) => (
                        <button
                          key={method.id}
                          type="button"
                          onClick={() => setCustomerDetails(prev => ({ ...prev, paymentMethod: method.id }))}
                          className={`p-3 rounded-xl border text-xs font-heading font-bold text-left transition-all ${
                            customerDetails.paymentMethod === method.id
                              ? isDark ? 'bg-white text-zinc-950 border-white shadow-sm' : 'bg-zinc-900 text-white border-zinc-900 shadow-sm'
                              : isDark ? 'bg-zinc-950 border-zinc-800 text-zinc-400' : 'bg-zinc-50 border-zinc-200 text-zinc-700'
                          }`}
                        >
                          {method.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Order Review Sidebar (5 cols) */}
              <div className={`lg:col-span-5 p-6 rounded-3xl border space-y-5 ${
                isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200 shadow-clean'
              }`}>
                <h3 className="font-heading font-bold text-base border-b pb-3 dark:border-zinc-800 border-zinc-200">
                  Review & Confirm
                </h3>

                <div className="space-y-3 max-h-48 overflow-y-auto">
                  {cartItems.map((item, i) => (
                    <div key={i} className="flex justify-between items-center text-xs">
                      <div>
                        <span className="font-heading font-bold">{item.name}</span>
                        <p className="text-[11px] text-zinc-400 font-mono">[{item.variant}] × {item.qty}</p>
                      </div>
                      <span className="font-mono font-bold">
                        PKR {item.price * item.qty}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="pt-3 border-t space-y-2 text-xs font-mono dark:border-zinc-800 border-zinc-200 text-zinc-500 dark:text-zinc-400">
                  <div className="flex justify-between">
                    <span>Subtotal:</span>
                    <span className="font-bold text-zinc-900 dark:text-white">PKR {subtotal}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Delivery:</span>
                    <span className="font-bold text-zinc-900 dark:text-white">PKR {deliveryFee}</span>
                  </div>
                  <div className="flex justify-between pt-2 border-t text-sm font-bold dark:border-zinc-800 border-zinc-200">
                    <span className="text-zinc-900 dark:text-white font-heading">Total Amount:</span>
                    <span className="text-emerald-500 font-mono text-base font-extrabold">PKR {grandTotal}</span>
                  </div>
                </div>

                {/* Final Place Order Button */}
                <button
                  onClick={handlePlaceOrder}
                  className="w-full py-4 rounded-2xl font-heading font-extrabold text-sm uppercase tracking-wider bg-emerald-500 hover:bg-emerald-600 text-white shadow-dopamine-glow transition-all active:scale-98 flex items-center justify-center gap-2"
                >
                  <Check className="w-5 h-5 stroke-[2.5]" />
                  <span>Place Order (PKR {grandTotal})</span>
                </button>
              </div>

            </div>
          </motion.div>
        )}

        {/* ========================================================================= */}
        {/* PAGE 5: ORDER DONE / CONFIRMED (DOPAMINE HIT GREEN TICK 🟢)               */}
        {/* ========================================================================= */}
        {activePage === 'success' && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="max-w-2xl mx-auto text-center space-y-8 py-6"
          >
            {/* ✨ THE DOPAMINE HIT GREEN TICK */}
            <div className="relative flex justify-center">
              <div className="w-28 h-28 rounded-full bg-emerald-500/10 dark:bg-emerald-500/20 flex items-center justify-center shadow-dopamine-glow dopamine-pop">
                <CheckCircle2 className="w-20 h-20 text-emerald-500 stroke-[2.2]" />
              </div>
            </div>

            {/* Headline and Order Reference */}
            <div>
              <span className="text-xs uppercase font-extrabold tracking-widest text-emerald-600 dark:text-emerald-400 font-mono">
                Order Received & Verified
              </span>
              <h1 className="font-heading font-black text-3xl sm:text-4xl tracking-tight mt-1">
                Zabardast! Order Confirmed 🎉
              </h1>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-2">
                Order Reference: <span className="font-mono font-bold text-zinc-900 dark:text-white">#{confirmedOrder ? confirmedOrder.orderId : 'ZG-928174'}</span>
              </p>
            </div>

            {/* Live Kitchen Tracker & Countdown */}
            <div className={`p-6 rounded-3xl border space-y-6 text-left transition-colors ${
              isDark ? 'bg-zinc-900/80 border-zinc-800' : 'bg-white border-zinc-200 shadow-clean'
            }`}>
              {/* Estimated Delivery Countdown */}
              <div className="flex items-center justify-between pb-4 border-b dark:border-zinc-800 border-zinc-200">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center font-bold">
                    <Clock className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-heading font-bold text-sm">Estimated Delivery Time</h4>
                    <p className="text-xs text-zinc-400">Rider is being assigned to your order</p>
                  </div>
                </div>

                <div className="text-right">
                  <span className="font-mono font-black text-2xl text-emerald-500">
                    {formatTimer(countdownSeconds)}
                  </span>
                  <span className="block text-[10px] text-zinc-400 uppercase font-mono">Mins Remaining</span>
                </div>
              </div>

              {/* Step Tracker */}
              <div className="grid grid-cols-4 gap-2 pt-2">
                {[
                  { step: '1', title: 'Confirmed', done: true },
                  { step: '2', title: 'Cooking 🍔', done: true },
                  { step: '3', title: 'On the Way 🛵', done: false },
                  { step: '4', title: 'Delivered 📍', done: false }
                ].map((st, sIdx) => (
                  <div key={sIdx} className="text-center space-y-1.5">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center mx-auto text-xs font-bold ${
                      st.done
                        ? 'bg-emerald-500 text-white shadow-sm'
                        : isDark ? 'bg-zinc-800 text-zinc-500' : 'bg-zinc-100 text-zinc-400'
                    }`}>
                      {st.done ? '✓' : st.step}
                    </div>
                    <span className="block text-[11px] font-heading font-bold text-zinc-500 dark:text-zinc-400">
                      {st.title}
                    </span>
                  </div>
                ))}
              </div>

              {/* Delivery Destination Card */}
              <div className={`p-4 rounded-2xl border text-xs space-y-1.5 ${
                isDark ? 'bg-zinc-950 border-zinc-800' : 'bg-zinc-50 border-zinc-200'
              }`}>
                <div className="flex items-center gap-1.5 font-heading font-bold text-zinc-900 dark:text-white">
                  <MapPin className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Delivering to: {confirmedOrder ? confirmedOrder.customer.name : customerDetails.name}</span>
                </div>
                <p className="text-zinc-500 dark:text-zinc-400 pl-5">
                  {confirmedOrder ? confirmedOrder.customer.address : customerDetails.address}
                </p>
                <div className="flex items-center gap-4 pl-5 pt-1 text-zinc-400 font-mono text-[11px]">
                  <span>Payment: {confirmedOrder ? confirmedOrder.customer.paymentMethod : customerDetails.paymentMethod}</span>
                  <span>Total: PKR {confirmedOrder ? confirmedOrder.grandTotal : grandTotal}</span>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <button
                onClick={() => {
                  setCartItems([]);
                  setActivePage('menu');
                }}
                className={`w-full sm:w-auto px-8 py-3.5 rounded-2xl font-heading font-bold text-xs uppercase tracking-wider ${
                  isDark ? 'bg-white text-zinc-950' : 'bg-zinc-900 text-white'
                }`}
              >
                Order More Food 🍔
              </button>

              <button
                onClick={() => setActivePage('chat')}
                className={`w-full sm:w-auto px-8 py-3.5 rounded-2xl font-heading font-bold text-xs uppercase tracking-wider border ${
                  isDark ? 'border-zinc-800 bg-zinc-900 text-white' : 'border-zinc-300 bg-white text-zinc-900'
                }`}
              >
                Chat with Rider / Support 💬
              </button>
            </div>
          </motion.div>
        )}

      </main>

      {/* --- 🥂 TOAST NOTIFICATION --- */}
      <AnimatePresence>
        {toastText && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-2xl border flex items-center gap-2.5 text-xs font-heading font-bold shadow-lg ${
              isDark ? 'bg-zinc-900 border-zinc-700 text-white' : 'bg-white border-zinc-300 text-zinc-900'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span>{toastText}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* --- 👑 FOOTER --- */}
      <footer className={`border-t py-8 px-4 mt-auto transition-colors ${
        isDark ? 'bg-[#050507] border-zinc-800/80 text-zinc-500' : 'bg-white border-zinc-200 text-zinc-400'
      }`}>
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-heading">
          <div className="flex items-center gap-2">
            <span className="font-bold text-zinc-900 dark:text-zinc-200">ZAIQA GRILL & FAST FOOD</span>
            <span>• Karachi, Pakistan</span>
          </div>
          <div className="flex items-center gap-4 font-mono text-[11px]">
            <span>Fast Food Delivery</span>
            <span>•</span>
            <span>Multi-Tier WhatsApp AI</span>
          </div>
        </div>
      </footer>

    </div>
  );
}
