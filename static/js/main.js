// main.js - محلل الشطرنج الجزائري المتقدم v3.1 - الإصدار المحسن والمصحح

// متغيرات عامة محسنة
let currentAnalysis = null;
let isAnalyzing = false;
let progressInterval = null;
let sessionCheckInterval = null;

// إعدادات التطبيق
const CONFIG = {
    API_TIMEOUT: 30000, // 30 ثانية
    PROGRESS_UPDATE_INTERVAL: 800, // 0.8 ثانية
    SESSION_CHECK_INTERVAL: 60000, // دقيقة واحدة
    NOTIFICATION_DURATION: 5000, // 5 ثواني
    MAX_NOTIFICATION_QUEUE: 3
};

// قائمة انتظار الإشعارات
let notificationQueue = [];

// تهيئة الصفحة المحسنة
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initializing Chess Analyzer Algeria v3.1...');
    
    initializeEventListeners();
    initializeGameCountOptions();
    checkSessionStatus();
    startSessionMonitoring();
    showWelcomeMessage();
    
    console.log('✅ Initialization completed!');
});

// في main.js، استبدل دالة checkSessionStatus بهذه:

async function checkSessionStatus() {
    try {
        const response = await fetch('/api/session_status', {
            timeout: CONFIG.API_TIMEOUT
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('📊 Session Status:', data);
            
            // التحقق من انتهاء صلاحية التحليل المتقدم
            if (data.has_advanced_analysis && data.analysis_expires_at) {
                const timeLeft = data.analysis_expires_at - Math.floor(Date.now() / 1000);
                if (timeLeft < 3600) { // أقل من ساعة
                    const hoursLeft = Math.floor(timeLeft / 3600);
                    const minutesLeft = Math.floor((timeLeft % 3600) / 60);
                    showNotification(`تنتهي صلاحية التحليل خلال ${hoursLeft > 0 ? hoursLeft + ' ساعات و ' : ''}${minutesLeft} دقيقة`, 'warning', 6000);
                }
            }
            
            updateUIBasedOnSession(data);
            return data;
        } else {
            console.warn('⚠️ Session check failed:', response.status);
            return null;
        }
    } catch (error) {
        console.error('❌ Session check error:', error);
        return null;
    }
}

// تحديث دالة validateSessionAndNavigate
async function validateSessionAndNavigate(url, pageName) {
    showNavigationProgress(true);
    
    try {
        const sessionStatus = await checkSessionStatus();
        
        if (sessionStatus && (sessionStatus.has_advanced_analysis || sessionStatus.has_basic_analysis)) {
            // التحقق من انتهاء الصلاحية
            if (sessionStatus.has_advanced_analysis && sessionStatus.analysis_expires_at) {
                const timeLeft = sessionStatus.analysis_expires_at - Math.floor(Date.now() / 1000);
                if (timeLeft <= 0) {
                    throw new Error('انتهت صلاحية التحليل');
                }
            }
            
            showNotification(`جارِ الانتقال إلى ${pageName}...`, 'info', 2000);
            
            setTimeout(() => {
                window.location.href = url;
            }, 500);
            
            return true;
        } else {
            throw new Error('لا يوجد تحليل صالح');
        }
    } catch (error) {
        showNavigationProgress(false);
        showNotification(error.message + '. يرجى إعادة التحليل.', 'error', 6000);
        return false;
    }
}

// تحديث واجهة المستخدم بناءً على حالة الجلسة
function updateUIBasedOnSession(sessionData) {
    const hasAnalysis = sessionData.has_basic_analysis || sessionData.has_advanced_analysis;
    
    if (hasAnalysis) {
        // إظهار رسالة ترحيب بالمستخدم
        const username = sessionData.advanced_analysis_username || sessionData.basic_analysis_username;
        if (username) {
            showSessionRestoreMessage(username, sessionData.advanced_analysis_games || sessionData.basic_analysis_games);
        }
    }
    
    // تحذير إذا كانت الجلسة كبيرة
    if (sessionData.session_size_kb > 3) {
        console.warn(`⚠️ Large session size: ${sessionData.session_size_kb.toFixed(2)} KB`);
    }
}

// مراقبة الجلسة الدورية
function startSessionMonitoring() {
    sessionCheckInterval = setInterval(checkSessionStatus, CONFIG.SESSION_CHECK_INTERVAL);
}

// رسالة استعادة الجلسة
function showSessionRestoreMessage(username, gamesCount) {
    const message = `مرحباً مجدداً! تم العثور على تحليل سابق لـ ${username} (${gamesCount} مباراة)`;
    showNotification(message, 'info', 3000);
}

// تهيئة مستمعي الأحداث المحسنة
function initializeEventListeners() {
    const usernameInput = document.getElementById('username');
    if (usernameInput) {
        usernameInput.addEventListener('keypress', handleEnterKey);
        usernameInput.addEventListener('input', debounce(handleUsernameInput, 500));
        usernameInput.addEventListener('focus', clearPreviousSearchResults);
        usernameInput.focus();
    }
    
    // تهيئة خيارات عدد المباريات
    document.querySelectorAll('input[name="maxGames"]').forEach(radio => {
        radio.addEventListener('change', updateGameCountDisplay);
    });
    
    // منع إرسال النماذج
    document.addEventListener('submit', function(e) {
        e.preventDefault();
    });
    
    // إضافة معالج لإغلاق الإشعارات بالمفتاح Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            clearAllNotifications();
        }
    });
}

// دالة debounce لتقليل استدعاءات API
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// تهيئة خيارات عدد المباريات المحسنة
function initializeGameCountOptions() {
    document.querySelectorAll('.game-count-option').forEach(option => {
        option.addEventListener('click', function() {
            // إزالة التحديد السابق مع تأثير سلس
            document.querySelectorAll('.game-count-option div').forEach(div => {
                div.classList.remove('border-blue-500', 'bg-blue-50');
                div.classList.add('border-gray-200');
                div.style.transform = 'scale(1)';
            });
            
            // تحديد الخيار الجديد مع تأثير سلس
            const div = this.querySelector('div');
            div.classList.remove('border-gray-200');
            div.classList.add('border-blue-500', 'bg-blue-50');
            div.style.transform = 'scale(1.05)';
            
            // تحديث الراديو
            const radio = this.querySelector('input[type="radio"]');
            radio.checked = true;
            
            // إضافة تأثير بصري
            this.style.animation = 'bounceIn 0.5s ease-out';
            setTimeout(() => {
                this.style.animation = '';
                div.style.transform = 'scale(1)';
            }, 500);
            
            // إشعار المستخدم
            const gameCount = radio.value;
            showNotification(`تم اختيار ${gameCount} مباراة للتحليل`, 'info', 2000);
        });
    });
}

// معالجة الضغط على Enter المحسنة
function handleEnterKey(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        
        if (isAnalyzing) {
            showNotification('التحليل قيد التشغيل، يرجى الانتظار...', 'warning', 2000);
            return;
        }
        
        const username = getUsername();
        if (!validateInput(username)) {
            return;
        }
        
        // تحديد نوع التحليل بناءً على الإعدادات الافتراضية
        const defaultAnalysis = document.querySelector('.analysis-type-btn.btn-primary');
        if (defaultAnalysis) {
            defaultAnalysis.click();
        } else {
            performQuickAnalysis();
        }
    }
}

// معالجة إدخال اسم المستخدم المحسنة
function handleUsernameInput(e) {
    const username = e.target.value.trim();
    
    if (username.length >= 3) {
        searchPlayer(username);
    } else if (username.length === 0) {
        hidePlayerSuggestions();
    }
}

// مسح نتائج البحث السابقة
function clearPreviousSearchResults() {
    hidePlayerSuggestions();
}

// البحث عن اللاعب المحسن
async function searchPlayer(username) {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        const response = await fetch(`/api/player_search?username=${encodeURIComponent(username)}`, {
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        const data = await response.json();
        
        if (data.success && data.player) {
            showPlayerSuggestion(data.player);
        } else {
            hidePlayerSuggestions();
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('🔍 Player search timeout');
        } else {
            console.error('❌ Player search error:', error);
        }
        hidePlayerSuggestions();
    }
}

// عرض اقتراح اللاعب المحسن
function showPlayerSuggestion(player) {
    const suggestionsDiv = document.getElementById('playerSuggestions');
    if (!suggestionsDiv) return;
    
    const avatar = player.avatar ? 
        `<img src="${player.avatar}" class="w-10 h-10 rounded-full border-2 border-blue-200" alt="${player.username}">` : 
        '<div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white font-bold text-lg">👤</div>';
    
    const title = player.title ? `<span class="bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full text-xs font-bold">${player.title}</span>` : '';
    const country = player.country ? `<span class="text-xs text-gray-500">🌍 ${player.country.split('/').pop()}</span>` : '';
    const followers = player.followers > 0 ? `<span class="text-xs text-gray-500">👥 ${player.followers.toLocaleString()} متابع</span>` : '';
    
    suggestionsDiv.innerHTML = `
        <div class="p-4 hover:bg-gradient-to-r hover:from-blue-50 hover:to-purple-50 cursor-pointer border-b transition-all duration-300" onclick="selectPlayer('${player.username}')">
            <div class="flex items-center space-x-4 space-x-reverse">
                ${avatar}
                <div class="flex-1">
                    <div class="flex items-center space-x-2 space-x-reverse mb-1">
                        <span class="font-bold text-lg text-gray-800">${player.username}</span>
                        ${title}
                    </div>
                    <div class="text-sm text-gray-600 mb-2">${player.name || 'لاعب شطرنج'}</div>
                    <div class="flex items-center space-x-3 space-x-reverse text-xs">
                        ${country}
                        ${followers}
                        ${player.is_streamer ? '<span class="bg-red-100 text-red-800 px-2 py-1 rounded-full">📺 مذيع</span>' : ''}
                    </div>
                </div>
                <div class="text-2xl text-green-500">✓</div>
            </div>
        </div>
    `;
    
    suggestionsDiv.classList.remove('hidden');
    suggestionsDiv.style.animation = 'slideDown 0.3s ease-out';
    
    // إخفاء الاقتراحات عند النقر خارجها
    setTimeout(() => {
        document.addEventListener('click', function hideOnClick(e) {
            if (!suggestionsDiv.contains(e.target) && !document.getElementById('username').contains(e.target)) {
                hidePlayerSuggestions();
                document.removeEventListener('click', hideOnClick);
            }
        });
    }, 100);
}

// إخفاء اقتراحات اللاعبين
function hidePlayerSuggestions() {
    const suggestionsDiv = document.getElementById('playerSuggestions');
    if (suggestionsDiv) {
        suggestionsDiv.style.animation = 'slideUp 0.3s ease-in';
        setTimeout(() => {
            suggestionsDiv.classList.add('hidden');
        }, 300);
    }
}

// اختيار لاعب من الاقتراحات
function selectPlayer(username) {
    const usernameInput = document.getElementById('username');
    if (usernameInput) {
        usernameInput.value = username;
        usernameInput.style.animation = 'pulse 0.5s ease-in-out';
        setTimeout(() => {
            usernameInput.style.animation = '';
        }, 500);
    }
    hidePlayerSuggestions();
    showNotification(`تم اختيار اللاعب: ${username}`, 'success', 2000);
}

// التحليل السريع المحسن
async function performQuickAnalysis() {
    const username = getUsername();
    const maxGames = getMaxGames();
    
    if (!validateInput(username)) return;
    
    if (isAnalyzing) {
        showNotification('التحليل قيد التشغيل بالفعل...', 'warning');
        return;
    }
    
    startAnalysis('التحليل السريع', [
        'جلب معلومات اللاعب...',
        'جلب المباريات الأخيرة...',
        'تحليل النتائج...',
        'حساب الإحصائيات...',
        'إعداد التقرير...'
    ]);
    
    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ username, max_games: maxGames }),
            timeout: CONFIG.API_TIMEOUT
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            displayQuickAnalysis(data);
            showNotification(`تم تحليل ${data.games.length} مباراة بنجاح! ⚡`, 'success');
            
            // تحليل إضافي للنصائح
            const advice = generateQuickAdvice(data);
            if (advice) {
                setTimeout(() => showNotification(advice, 'info', 7000), 2000);
            }
        } else {
            throw new Error(data.error || 'فشل في التحليل');
        }
    } catch (error) {
        console.error('❌ Quick analysis error:', error);
        let errorMessage = 'خطأ في الاتصال بالخادم';
        
        if (error.message.includes('404')) {
            errorMessage = 'لم يتم العثور على اللاعب. تأكد من اسم المستخدم.';
        } else if (error.message.includes('timeout')) {
            errorMessage = 'انتهت مهلة الاتصال. حاول مرة أخرى.';
        } else if (error.message) {
            errorMessage = error.message;
        }
        
        showNotification(errorMessage, 'error');
    } finally {
        stopAnalysis();
    }
}

// التحليل المتقدم المحسن
async function performAdvancedAnalysis() {
    const username = getUsername();
    const maxGames = getMaxGames();
    
    if (!validateInput(username)) return;
    
    if (isAnalyzing) {
        showNotification('التحليل قيد التشغيل بالفعل...', 'warning');
        return;
    }
    
    startAnalysis('التحليل المتقدم', [
        'جلب معلومات اللاعب...',
        'جمع المباريات من الأرشيف...',
        'تحليل الافتتاحيات والدفاعات...',
        'تحليل نقاط القوة والضعف...',
        'حساب اتجاهات الأداء...',
        'إعداد الإحصائيات المتقدمة...',
        'إنشاء التوصيات المخصصة...',
        'إنهاء التحليل...'
    ]);
    
    try {
        const response = await fetch('/analyze_advanced', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ username, max_games: maxGames }),
            timeout: CONFIG.API_TIMEOUT * 2 // وقت أطول للتحليل المتقدم
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            currentAnalysis = data.analysis;
            showAnalysisOptionsModal(data.analysis);
            showNotification('تم التحليل المتقدم بنجاح! 🧠', 'success');
            
            // تحديث حالة الجلسة
            setTimeout(checkSessionStatus, 1000);
        } else {
            throw new Error(data.error || 'فشل في التحليل المتقدم');
        }
    } catch (error) {
        console.error('❌ Advanced analysis error:', error);
        let errorMessage = 'خطأ في التحليل المتقدم';
        
        if (error.message.includes('404')) {
            errorMessage = 'لم يتم العثور على اللاعب أو مباريات كافية للتحليل';
        } else if (error.message.includes('timeout')) {
            errorMessage = 'التحليل يستغرق وقتاً أطول. حاول تقليل عدد المباريات.';
        } else if (error.message) {
            errorMessage = error.message;
        }
        
        showNotification(errorMessage, 'error', 8000);
    } finally {
        stopAnalysis();
    }
}

// إكمال دالة generateQuickAdvice
function generateQuickAdvice(data) {
    const stats = data.stats;
    const advice = [];
    
    if (stats.win_rate > 70) {
        advice.push('🎉 أداء ممتاز! استمر في نفس الاستراتيجية');
    } else if (stats.win_rate > 50) {
        advice.push('👍 أداء جيد! فكر في التحليل المتقدم لمزيد من التحسينات');
    } else if (stats.win_rate < 40) {
        advice.push('💪 هناك مجال للتحسين. ركز على دراسة الافتتاحيات الأساسية');
    }
    
    if (stats.avg_moves < 25) {
        advice.push('⚡ مبارياتك سريعة! حاول التأني أكثر في اتخاذ القرارات');
    } else if (stats.avg_moves > 60) {
        advice.push('🕐 مبارياتك طويلة! قد تحتاج لتحسين الدقة في النهايات');
    }
    
    if (stats.white_win_rate > stats.black_win_rate + 20) {
        advice.push('⚪ أقوى بالقطع البيضاء - طور دفاعاتك بالقطع السوداء');
    } else if (stats.black_win_rate > stats.white_win_rate + 10) {
        advice.push('⚫ دفاع ممتاز! حاول تطوير أسلوب هجومي بالقطع البيضاء');
    }
    
    return advice.length > 0 ? advice[Math.floor(Math.random() * advice.length)] : null;
}

// عرض نافذة خيارات التحليل المتقدم - المحسنة
function showAnalysisOptionsModal(analysis) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-60 z-50 flex items-center justify-center p-4 backdrop-blur-sm';
    modal.innerHTML = `
        <div class="bg-white rounded-3xl p-8 max-w-5xl w-full max-h-[90vh] overflow-y-auto shadow-2xl animate-bounce-in">
            <div class="text-center mb-8">
                <div class="text-7xl mb-4 animate-bounce">🎉</div>
                <h2 class="text-4xl font-bold mb-4 arabic-text bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                    تم التحليل المتقدم بنجاح!
                </h2>
                <p class="text-gray-600 arabic-text text-lg leading-relaxed">
                    تم تحليل <span class="font-bold text-blue-600">${analysis.total_analyzed}</span> مباراة مع 
                    <span class="font-bold text-purple-600">${analysis.advanced_stats.openings_analysis.total_openings_count}</span> افتتاحية مختلفة
                </p>
            </div>
            
            <!-- Statistics Cards -->
            <div class="grid md:grid-cols-4 gap-4 mb-8">
                <div class="bg-gradient-to-br from-blue-50 to-blue-100 p-6 rounded-2xl text-center border border-blue-200">
                    <div class="text-4xl font-bold text-blue-600 mb-2">${analysis.total_analyzed}</div>
                    <div class="text-sm text-gray-600 font-medium">مباراة محللة</div>
                </div>
                <div class="bg-gradient-to-br from-green-50 to-green-100 p-6 rounded-2xl text-center border border-green-200">
                    <div class="text-4xl font-bold text-green-600 mb-2">${calculateWinRate(analysis.games)}%</div>
                    <div class="text-sm text-gray-600 font-medium">معدل الفوز</div>
                </div>
                <div class="bg-gradient-to-br from-purple-50 to-purple-100 p-6 rounded-2xl text-center border border-purple-200">
                    <div class="text-4xl font-bold text-purple-600 mb-2">${analysis.advanced_stats.openings_analysis.total_openings_count}</div>
                    <div class="text-sm text-gray-600 font-medium">افتتاحيات مختلفة</div>
                </div>
                <div class="bg-gradient-to-br from-orange-50 to-orange-100 p-6 rounded-2xl text-center border border-orange-200">
                    <div class="text-4xl font-bold text-orange-600 mb-2">${analysis.advanced_stats.trend_analysis.trend || 'مستقر'}</div>
                    <div class="text-sm text-gray-600 font-medium">اتجاه الأداء</div>
                </div>
            </div>
            
            <!-- Quick Insights -->
            <div class="bg-gradient-to-r from-gray-50 to-gray-100 p-6 rounded-2xl mb-8">
                <h3 class="text-xl font-bold mb-4 arabic-text flex items-center">
                    <span class="text-2xl ml-3">💡</span>
                    نظرة سريعة على النتائج
                </h3>
                <div class="grid md:grid-cols-2 gap-6">
                    <div>
                        <h4 class="font-semibold text-green-800 mb-2">🎯 أبرز نقاط القوة:</h4>
                        <ul class="text-sm space-y-1">
                            ${analysis.advanced_stats.strengths_and_weaknesses.strengths.slice(0, 3).map(strength => 
                                `<li class="text-green-700">• ${strength}</li>`
                            ).join('')}
                        </ul>
                    </div>
                    <div>
                        <h4 class="font-semibold text-orange-800 mb-2">🔧 مجالات للتحسين:</h4>
                        <ul class="text-sm space-y-1">
                            ${analysis.advanced_stats.strengths_and_weaknesses.weaknesses.slice(0, 3).map(weakness => 
                                `<li class="text-orange-700">• ${weakness}</li>`
                            ).join('')}
                        </ul>
                    </div>
                </div>
            </div>
            
            <!-- Action Buttons -->
            <div class="space-y-4">
                <button onclick="navigateToDeepAnalysis()" 
                        class="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-4 px-6 rounded-2xl hover:from-blue-700 hover:to-purple-700 transition duration-300 text-lg font-semibold shadow-lg hover:shadow-xl transform hover:-translate-y-1">
                    <span class="text-2xl ml-3">🧠</span>
                    عرض التحليل العميق الكامل
                </button>
                
                <div class="grid md:grid-cols-2 gap-4">
                    <button onclick="navigateToStatistics()" 
                            class="w-full bg-gradient-to-r from-green-600 to-blue-600 text-white py-3 px-4 rounded-xl hover:from-green-700 hover:to-blue-700 transition duration-300 font-semibold shadow-md hover:shadow-lg transform hover:-translate-y-0.5">
                        <span class="text-xl ml-2">📈</span>
                        الإحصائيات المتقدمة
                    </button>
                    
                    <button onclick="navigateToFilterGames()" 
                            class="w-full bg-gradient-to-r from-orange-600 to-red-600 text-white py-3 px-4 rounded-xl hover:from-orange-700 hover:to-red-700 transition duration-300 font-semibold shadow-md hover:shadow-lg transform hover:-translate-y-0.5">
                        <span class="text-xl ml-2">🔍</span>
                        تصفية المباريات
                    </button>
                </div>
                
                <div class="grid grid-cols-2 gap-4">
                    <button onclick="exportAdvancedResults()" 
                            class="bg-gray-600 text-white py-3 px-4 rounded-xl hover:bg-gray-700 transition duration-300 font-medium">
                        <span class="text-lg ml-2">📊</span>
                        تصدير التحليل
                    </button>
                    <button onclick="closeModal()" 
                            class="bg-red-600 text-white py-3 px-4 rounded-xl hover:bg-red-700 transition duration-300 font-medium">
                        <span class="text-lg ml-2">✕</span>
                        إغلاق
                    </button>
                </div>
            </div>
            
            <!-- Progress indicator for navigation -->
            <div id="navigationProgress" class="hidden mt-4">
                <div class="bg-gray-200 rounded-full h-2">
                    <div class="bg-blue-600 h-2 rounded-full transition-all duration-500" style="width: 0%"></div>
                </div>
                <p class="text-center text-sm text-gray-600 mt-2">جارِ الانتقال...</p>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // إضافة تأثير الظهور
    setTimeout(() => {
        modal.style.animation = 'fadeIn 0.5s ease-out';
    }, 10);
    
    // الدوال المحسنة للانتقال مع معالجة الأخطاء
    window.navigateToDeepAnalysis = async () => {
        if (await validateSessionAndNavigate('/deep_analysis', 'التحليل العميق')) {
            closeModalAndCleanup();
        }
    };
    
    window.navigateToStatistics = async () => {
        if (await validateSessionAndNavigate('/statistics', 'الإحصائيات المتقدمة')) {
            closeModalAndCleanup();
        }
    };
    
    window.navigateToFilterGames = async () => {
        if (await validateSessionAndNavigate('/filter_games', 'تصفية المباريات')) {
            closeModalAndCleanup();
        }
    };
    
    window.closeModal = closeModalAndCleanup;
    
    function closeModalAndCleanup() {
        modal.style.animation = 'fadeOut 0.3s ease-in';
        setTimeout(() => {
            if (document.body.contains(modal)) {
                document.body.removeChild(modal);
            }
        }, 300);
        
        // تنظيف الدوال العامة
        delete window.navigateToDeepAnalysis;
        delete window.navigateToStatistics;
        delete window.navigateToFilterGames;
        delete window.closeModal;
    }
    
    // إضافة مستمع لإغلاق النافذة عند النقر خارجها
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModalAndCleanup();
        }
    });
    
    // إضافة مستمع للمفتاح Escape
    document.addEventListener('keydown', function escapeHandler(e) {
        if (e.key === 'Escape') {
            closeModalAndCleanup();
            document.removeEventListener('keydown', escapeHandler);
        }
    });
}

// التحقق من الجلسة والانتقال
async function validateSessionAndNavigate(url, pageName) {
    showNavigationProgress(true);
    
    try {
        const sessionStatus = await checkSessionStatus();
        
        if (sessionStatus && (sessionStatus.has_advanced_analysis || sessionStatus.has_basic_analysis)) {
            showNotification(`جارِ الانتقال إلى ${pageName}...`, 'info', 2000);
            
            // تأخير قصير لإظهار التقدم
            setTimeout(() => {
                window.location.href = url;
            }, 500);
            
            return true;
        } else {
            throw new Error('انتهت صلاحية الجلسة');
        }
    } catch (error) {
        showNavigationProgress(false);
        showNotification('انتهت صلاحية الجلسة. يرجى إعادة التحليل.', 'error', 6000);
        return false;
    }
}

// إظهار تقدم الانتقال
function showNavigationProgress(show) {
    const progressDiv = document.getElementById('navigationProgress');
    if (progressDiv) {
        if (show) {
            progressDiv.classList.remove('hidden');
            let progress = 0;
            const interval = setInterval(() => {
                progress += 10;
                const bar = progressDiv.querySelector('.bg-blue-600');
                if (bar) {
                    bar.style.width = `${Math.min(progress, 90)}%`;
                }
                if (progress >= 90) {
                    clearInterval(interval);
                }
            }, 50);
        } else {
            progressDiv.classList.add('hidden');
        }
    }
}

// عرض التحليل السريع المحسن
function displayQuickAnalysis(data) {
    const resultsDiv = document.getElementById('results');
    const contentDiv = document.getElementById('analysisContent');
    
    const html = `
        <div class="animate-fade-in">
            <!-- Header Section -->
            <div class="text-center mb-8">
                <div class="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-6 rounded-2xl">
                    <h2 class="text-3xl font-bold mb-2">⚡ التحليل السريع مكتمل</h2>
                    <p class="text-blue-100">نتائج تحليل ${data.stats.total_games} مباراة للاعب ${data.username}</p>
                </div>
            </div>
            
            <!-- Main Stats Grid -->
            <div class="grid lg:grid-cols-2 gap-8 mb-8">
                <div class="bg-gradient-to-br from-blue-50 to-blue-100 p-6 rounded-2xl border border-blue-200">
                    <h3 class="text-xl font-bold text-blue-800 mb-4 arabic-text flex items-center">
                        <span class="text-2xl ml-3">👤</span>
                        معلومات اللاعب
                    </h3>
                    <div class="space-y-3">
                        <div class="flex justify-between items-center">
                            <span class="text-gray-700">الاسم:</span>
                            <span class="font-semibold text-lg">${data.username}</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-gray-700">المباريات المحللة:</span>
                            <span class="font-semibold text-blue-600">${data.stats.total_games}</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-gray-700">معدل الفوز:</span>
                            <span class="font-bold text-green-600 text-xl">${data.stats.win_rate}%</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-gray-700">متوسط النقلات:</span>
                            <span class="font-semibold">${data.stats.avg_moves}</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-gray-700">متوسط جودة المباراة:</span>
                            <span class="font-semibold text-purple-600">${data.stats.avg_quality}/10</span>
                        </div>
                    </div>
                </div>
                
                <div class="bg-gradient-to-br from-green-50 to-green-100 p-6 rounded-2xl border border-green-200">
                    <h3 class="text-xl font-bold text-green-800 mb-4 arabic-text flex items-center">
                        <span class="text-2xl ml-3">📊</span>
                        توزيع النتائج
                    </h3>
                    <div class="grid grid-cols-3 gap-4 text-center mb-4">
                        <div class="bg-white p-4 rounded-xl shadow-sm">
                            <div class="text-2xl font-bold text-green-600">${data.stats.wins}</div>
                            <div class="text-sm text-gray-600">انتصار</div>
                            <div class="w-full bg-gray-200 rounded-full h-2 mt-2">
                                <div class="bg-green-600 h-2 rounded-full" style="width: ${(data.stats.wins / data.stats.total_games) * 100}%"></div>
                            </div>
                        </div>
                        <div class="bg-white p-4 rounded-xl shadow-sm">
                            <div class="text-2xl font-bold text-red-600">${data.stats.losses}</div>
                            <div class="text-sm text-gray-600">هزيمة</div>
                            <div class="w-full bg-gray-200 rounded-full h-2 mt-2">
                                <div class="bg-red-600 h-2 rounded-full" style="width: ${(data.stats.losses / data.stats.total_games) * 100}%"></div>
                            </div>
                        </div>
                        <div class="bg-white p-4 rounded-xl shadow-sm">
                            <div class="text-2xl font-bold text-yellow-600">${data.stats.draws}</div>
                            <div class="text-sm text-gray-600">تعادل</div>
                            <div class="w-full bg-gray-200 rounded-full h-2 mt-2">
                                <div class="bg-yellow-600 h-2 rounded-full" style="width: ${(data.stats.draws / data.stats.total_games) * 100}%"></div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Performance by Color -->
                    <div class="mt-4 pt-4 border-t border-green-200">
                        <h4 class="font-semibold mb-2">الأداء حسب اللون:</h4>
                        <div class="grid grid-cols-2 gap-2 text-sm">
                            <div class="flex items-center justify-between">
                                <span class="flex items-center"><span class="text-lg mr-2">⚪</span>أبيض:</span>
                                <span class="font-semibold">${data.stats.white_win_rate}%</span>
                            </div>
                            <div class="flex items-center justify-between">
                                <span class="flex items-center"><span class="text-lg mr-2">⚫</span>أسود:</span>
                                <span class="font-semibold">${data.stats.black_win_rate}%</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Recent Games -->
            <div class="mb-8">
                <h3 class="text-2xl font-bold mb-6 arabic-text flex items-center">
                    <span class="text-3xl ml-3">📋</span>
                    آخر 5 مباريات
                </h3>
                <div class="space-y-4">
                    ${data.games.slice(0, 5).map((game, index) => `
                        <div class="border-2 border-gray-200 rounded-xl p-4 hover:shadow-lg hover:border-blue-300 transition duration-300 cursor-pointer bg-white" onclick="viewGameDetails(${index})">
                            <div class="flex justify-between items-center">
                                <div class="flex items-center space-x-4 space-x-reverse">
                                    <span class="result-badge ${getResultClass(game.player_result)} px-3 py-2 rounded-full text-sm font-bold border-2">
                                        ${game.player_result}
                                    </span>
                                    <div class="text-2xl">${game.player_color === 'white' ? '⚪' : '⚫'}</div>
                                    <div>
                                        <h4 class="font-bold text-lg">${game.white_player} ضد ${game.black_player}</h4>
                                        <p class="text-sm text-gray-600">${game.opening} • ${game.total_moves} نقلة • جودة: ${game.game_quality || 'غير محدد'}/10</p>
                                        <p class="text-xs text-gray-500">${game.time_control} • ${game.rated ? 'مُقيمة' : 'غير مُقيمة'}</p>
                                    </div>
                                </div>
                                <div class="text-right">
                                    <div class="text-sm font-medium text-gray-500">${game.date}</div>
                                    <div class="text-xs text-gray-400">${game.game_duration} دقيقة</div>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
            
            <!-- Action Buttons -->
            <div class="flex flex-col sm:flex-row justify-center gap-4">
                <button onclick="performAdvancedAnalysis()" 
                        class="bg-gradient-to-r from-purple-600 to-purple-700 text-white px-8 py-4 rounded-xl hover:from-purple-700 hover:to-purple-800 transition duration-300 shadow-lg hover:shadow-xl transform hover:-translate-y-1 text-lg font-semibold">
                    <span class="text-2xl ml-3">🧠</span>
                    التحليل المتقدم
                </button>
                
                <button onclick="viewBasicResults()" 
                        class="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-8 py-4 rounded-xl hover:from-blue-700 hover:to-blue-800 transition duration-300 shadow-lg hover:shadow-xl transform hover:-translate-y-1 text-lg font-semibold">
                    <span class="text-2xl ml-3">📋</span>
                    عرض جميع المباريات
                </button>
                
                <button onclick="exportBasicResults()" 
                        class="bg-gradient-to-r from-green-600 to-green-700 text-white px-6 py-4 rounded-xl hover:from-green-700 hover:to-green-800 transition duration-300 shadow-lg hover:shadow-xl transform hover:-translate-y-1 font-semibold">
                    <span class="text-xl ml-2">📊</span>
                    تصدير
                </button>
            </div>
        </div>
    `;
    
    contentDiv.innerHTML = html;
    resultsDiv.classList.remove('hidden');
    
    // تمرير سلس مع تأثير بصري
    setTimeout(() => {
        resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
    
    // إضافة تأثيرات بصرية للبطاقات
    setTimeout(() => {
        document.querySelectorAll('.animate-fade-in > *').forEach((el, index) => {
            el.style.animation = `slideUp 0.6s ease-out ${index * 0.1}s both`;
        });
    }, 200);
}

// الوظائف المساعدة المحسنة
function getUsername() {
    const input = document.getElementById('username');
    return input ? input.value.trim() : '';
}

function getMaxGames() {
    const selectedRadio = document.querySelector('input[name="maxGames"]:checked');
    return selectedRadio ? parseInt(selectedRadio.value) : 25;
}

function validateInput(username) {
    if (!username) {
        showNotification('يرجى إدخال اسم المستخدم', 'error');
        const usernameInput = document.getElementById('username');
        if (usernameInput) {
            usernameInput.focus();
            usernameInput.style.animation = 'shake 0.5s ease-in-out';
            setTimeout(() => {
                usernameInput.style.animation = '';
            }, 500);
        }
        return false;
    }
    
    if (username.length < 3) {
        showNotification('اسم المستخدم يجب أن يكون 3 أحرف على الأقل', 'error');
        return false;
    }
    
    if (username.length > 25) {
        showNotification('اسم المستخدم طويل جداً (حد أقصى 25 حرف)', 'error');
        return false;
    }
    
    // التحقق من الأحرف المسموحة
    const validPattern = /^[a-zA-Z0-9_-]+$/;
    if (!validPattern.test(username)) {
        showNotification('اسم المستخدم يحتوي على أحرف غير مسموحة', 'error');
        return false;
    }
    
    return true;
}

function calculateWinRate(games) {
    if (!games || games.length === 0) return 0;
    const wins = games.filter(g => g.player_result === 'فوز').length;
    return Math.round((wins / games.length) * 100);
}

function getResultClass(result) {
    const classes = {
        'فوز': 'bg-green-100 text-green-800 border-green-300',
        'خسارة': 'bg-red-100 text-red-800 border-red-300',
        'تعادل': 'bg-yellow-100 text-yellow-800 border-yellow-300'
    };
    return classes[result] || 'bg-gray-100 text-gray-800 border-gray-300';
}

// وظائف التحكم في التحليل المحسنة
function startAnalysis(type, steps = []) {
    isAnalyzing = true;
    
    const progressSection = document.getElementById('progressSection');
    if (progressSection) {
        progressSection.classList.remove('hidden');
        simulateProgress(type, steps);
    }
    
    // تعطيل العناصر التفاعلية
    document.querySelectorAll('.analysis-type-btn').forEach(btn => {
        btn.disabled = true;
        btn.classList.add('opacity-50', 'cursor-not-allowed');
    });
    
    const usernameInput = document.getElementById('username');
    if (usernameInput) {
        usernameInput.disabled = true;
    }
    
    document.querySelectorAll('.game-count-option').forEach(option => {
        option.style.pointerEvents = 'none';
        option.classList.add('opacity-60');
    });
    
    console.log(`🔄 Started ${type}...`);
}

function stopAnalysis() {
    isAnalyzing = false;
    
    const progressSection = document.getElementById('progressSection');
    if (progressSection) {
        // إكمال شريط التقدم أولاً
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        const progressPercent = document.getElementById('progressPercent');
        
        if (progressBar) {
            progressBar.style.width = '100%';
        }
        if (progressText) {
            progressText.textContent = 'اكتمل!';
        }
        if (progressPercent) {
            progressPercent.textContent = '100%';
        }
        
        // إخفاء بعد ثانية
        setTimeout(() => {
            progressSection.classList.add('hidden');
        }, 1000);
    }
    
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
    
    // تفعيل العناصر التفاعلية
    document.querySelectorAll('.analysis-type-btn').forEach(btn => {
        btn.disabled = false;
        btn.classList.remove('opacity-50', 'cursor-not-allowed');
    });
    
    const usernameInput = document.getElementById('username');
    if (usernameInput) {
        usernameInput.disabled = false;
    }
    
    document.querySelectorAll('.game-count-option').forEach(option => {
        option.style.pointerEvents = 'auto';
        option.classList.remove('opacity-60');
    });
    
    console.log('✅ Analysis completed!');
}

function simulateProgress(type, steps) {
    let progress = 0;
    let currentStep = 0;
    const stepIncrement = 95 / steps.length; // 95% للخطوات، 5% للإنهاء
    
    progressInterval = setInterval(() => {
        const randomIncrement = Math.random() * 8 + 2; // 2-10%
        progress = Math.min(progress + randomIncrement, (currentStep + 1) * stepIncrement);
        
        // الانتقال للخطوة التالية
        if (progress >= (currentStep + 1) * stepIncrement && currentStep < steps.length - 1) {
            currentStep++;
        }
        
        const currentStepText = steps[currentStep] || 'جارِ الإنهاء...';
        updateProgress(progress, currentStepText);
        
        // إيقاف عند 95% للسماح للعملية الفعلية بالإنهاء
        if (progress >= 95) {
            clearInterval(progressInterval);
            progressInterval = null;
        }
    }, CONFIG.PROGRESS_UPDATE_INTERVAL);
}

function updateProgress(percent, text) {
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressPercent = document.getElementById('progressPercent');
    
    if (progressBar) {
        progressBar.style.width = `${percent}%`;
        progressBar.style.background = `linear-gradient(90deg, 
            #3b82f6 ${percent}%, 
            #8b5cf6 ${Math.min(percent + 20, 100)}%)`;
    }
    if (progressText) {
        progressText.textContent = text;
    }
    if (progressPercent) {
        progressPercent.textContent = `${Math.round(percent)}%`;
    }
}

// نظام الإشعارات المحسن والمتطور
function showNotification(message, type = 'info', duration = CONFIG.NOTIFICATION_DURATION) {
    // إدارة قائمة انتظار الإشعارات
    if (notificationQueue.length >= CONFIG.MAX_NOTIFICATION_QUEUE) {
        const oldestNotification = notificationQueue.shift();
        removeNotification(oldestNotification.querySelector('button'));
    }
    
    // إنشاء container الإشعارات إذا لم يكن موجوداً
    let container = document.getElementById('notifications');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notifications';
        container.className = 'fixed top-4 left-4 z-50 space-y-3 max-w-sm';
        document.body.appendChild(container);
    }
    
    const notification = document.createElement('div');
    const notificationId = 'notification_' + Date.now();
    notification.id = notificationId;
    notification.className = 'transform translate-x-full opacity-0 transition-all duration-500 p-4 rounded-xl shadow-2xl border-l-4 backdrop-blur-sm';
    
    const config = {
        success: {
            bg: 'bg-gradient-to-r from-green-500 to-green-600',
            border: 'border-green-400',
            icon: '✅',
            title: 'نجح!'
        },
        error: {
            bg: 'bg-gradient-to-r from-red-500 to-red-600',
            border: 'border-red-400',
            icon: '❌',
            title: 'خطأ!'
        },
        warning: {
            bg: 'bg-gradient-to-r from-yellow-500 to-orange-500',
            border: 'border-yellow-400',
            icon: '⚠️',
            title: 'تحذير!'
        },
        info: {
            bg: 'bg-gradient-to-r from-blue-500 to-blue-600',
            border: 'border-blue-400',
            icon: 'ℹ️',
            title: 'معلومة'
        }
    };
    
    const typeConfig = config[type] || config.info;
    notification.className += ` ${typeConfig.bg} ${typeConfig.border} text-white`;
    
    notification.innerHTML = `
        <div class="flex items-start justify-between">
            <div class="flex items-center flex-1">
                <span class="text-2xl ml-3 animate-bounce">${typeConfig.icon}</span>
                <div class="flex-1">
                    <div class="font-bold text-sm mb-1">${typeConfig.title}</div>
                    <div class="arabic-text text-sm leading-relaxed">${message}</div>
                </div>
            </div>
            <button onclick="removeNotification(this)" 
                    class="ml-4 hover:bg-white hover:bg-opacity-20 rounded-full p-1 transition duration-200 text-xl font-bold">
                ✕
            </button>
        </div>
        
        <!-- Progress bar for duration -->
        <div class="mt-3 bg-white bg-opacity-20 rounded-full h-1 overflow-hidden">
            <div class="bg-white h-1 rounded-full animate-progress" style="width: 100%; animation-duration: ${duration}ms;"></div>
        </div>
    `;
    
    container.appendChild(notification);
    notificationQueue.push(notification);
    
    // تأثير الظهور المحسن
    requestAnimationFrame(() => {
        notification.classList.remove('translate-x-full', 'opacity-0');
        notification.classList.add('translate-x-0', 'opacity-100');
    });
    
    // إضافة تأثير اهتزاز للأخطاء
    if (type === 'error') {
        setTimeout(() => {
            notification.style.animation = 'shake 0.5s ease-in-out';
        }, 500);
    }
    
    // إزالة تلقائية
    setTimeout(() => {
        removeNotification(notification.querySelector('button'));
    }, duration);
    
    console.log(`📢 Notification (${type}): ${message}`);
}

function removeNotification(button) {
    const notification = button.closest('[id^="notification_"]');
    if (notification) {
        // إزالة من قائمة الانتظار
        const index = notificationQueue.indexOf(notification);
        if (index > -1) {
            notificationQueue.splice(index, 1);
        }
        
        // تأثير الاختفاء
        notification.classList.add('translate-x-full', 'opacity-0', 'scale-95');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 500);
    }
}

function clearAllNotifications() {
    notificationQueue.forEach(notification => {
        const button = notification.querySelector('button');
        if (button) {
            removeNotification(button);
        }
    });
    notificationQueue = [];
}

// وظائف التنقل والتصدير
function viewBasicResults() {
    window.location.href = '/results';
}

function viewGameDetails(gameIndex) {
    const url = `/game_analysis/${gameIndex}`;
    window.open(url, '_blank');
}

function exportBasicResults() {
    const analysis = currentAnalysis || sessionStorage.getItem('basic_analysis');
    if (!analysis) {
        showNotification('لا توجد نتائج للتصدير', 'error');
        return;
    }
    
    try {
        const data = typeof analysis === 'string' ? JSON.parse(analysis) : analysis;
        const exportData = {
            username: data.username,
            export_date: new Date().toISOString(),
            analysis_type: 'basic',
            stats: data.stats,
            games_sample: data.games.slice(0, 5)
        };
        
        downloadJSON(exportData, `chess-basic-${data.username}-${new Date().toISOString().split('T')[0]}.json`);
        showNotification('تم تصدير النتائج الأساسية بنجاح! 📁', 'success');
    } catch (error) {
        console.error('Export error:', error);
        showNotification('فشل في تصدير النتائج', 'error');
    }
}

function exportAdvancedResults() {
    if (!currentAnalysis) {
        showNotification('لا توجد نتائج متقدمة للتصدير', 'error');
        return;
    }
    
    try {
        const exportData = {
            ...currentAnalysis,
            export_date: new Date().toISOString(),
            export_version: '3.1'
        };
        
        downloadJSON(exportData, `chess-advanced-${currentAnalysis.username}-${new Date().toISOString().split('T')[0]}.json`);
        showNotification('تم تصدير التحليل المتقدم بنجاح! 📊', 'success');
    } catch (error) {
        console.error('Export error:', error);
        showNotification('فشل في تصدير التحليل المتقدم', 'error');
    }
}

function downloadJSON(data, filename) {
    try {
        const jsonString = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.style.display = 'none';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Download error:', error);
        throw error;
    }
}

// وظائف أخرى
function clearResults() {
    const resultsDiv = document.getElementById('results');
    if (resultsDiv) {
        resultsDiv.style.animation = 'fadeOut 0.5s ease-in';
        setTimeout(() => {
            resultsDiv.classList.add('hidden');
            resultsDiv.style.animation = '';
        }, 500);
        
        currentAnalysis = null;
        document.getElementById('username').value = '';
        showNotification('تم مسح النتائج', 'info', 2000);
    }
}

function updateGameCountDisplay() {
    const selected = document.querySelector('input[name="maxGames"]:checked');
    if (selected) {
        console.log(`📊 Selected games count: ${selected.value}`);
    }
}

function showWelcomeMessage() {
    setTimeout(() => {
        const messages = [
            'مرحباً بك في محلل الشطرنج الجزائري المتقدم! 🇩🇿',
            'اكتشف أسرار لعبك مع أقوى أداة تحليل! ♔',
            'جاهز لتحليل مبارياتك؟ ابدأ الآن! 🚀'
        ];
        const randomMessage = messages[Math.floor(Math.random() * messages.length)];
        showNotification(randomMessage, 'info', 4000);
    }, 1500);
}

// إضافة CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
        20%, 40%, 60%, 80% { transform: translateX(5px); }
    }
    
    @keyframes slideDown {
        from { transform: translateY(-10px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    
    @keyframes slideUp {
        from { transform: translateY(0); opacity: 1; }
        to { transform: translateY(-10px); opacity: 0; }
    }
    
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
    
    @keyframes animate-progress {
        from { width: 100%; }
        to { width: 0%; }
    }
    
    .animate-progress {
        animation: animate-progress linear forwards;
    }
`;
document.head.appendChild(style);

// منع إعادة تشغيل الصفحة أثناء التحليل
window.addEventListener('beforeunload', function(e) {
    if (isAnalyzing) {
        const message = 'التحليل قيد التشغيل. هل أنت متأكد من الرغبة في المغادرة؟';
        e.preventDefault();
        e.returnValue = message;
        return message;
    }
});

// تنظيف الذاكرة عند إغلاق الصفحة
window.addEventListener('unload', function() {
    if (progressInterval) {
        clearInterval(progressInterval);
    }
    if (sessionCheckInterval) {
        clearInterval(sessionCheckInterval);
    }
    clearAllNotifications();
});

// تحسين الأداء - lazy loading للصور
if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    observer.unobserve(img);
                }
            }
        });
    });

    // مراقبة الصور الكسولة
    setTimeout(() => {
        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }, 1000);
}

console.log('✅ Chess Analyzer Algeria v3.1 - Main.js loaded successfully!');
