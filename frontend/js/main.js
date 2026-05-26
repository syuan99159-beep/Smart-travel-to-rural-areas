// API base selection
// If window.__API_BASE__ is set (via hosting or a build), use that.
// If running on localhost, default to local Flask backend.
const _API_BASE_RAW = (window.__API_BASE__ !== undefined) ? window.__API_BASE__ : (location.hostname === 'localhost' || location.hostname === '127.0.0.1' ? 'http://127.0.0.1:5003' : '');
const API_BASE = _API_BASE_RAW ? _API_BASE_RAW.replace(/\/$/, '') : '';

function apiUrl(path) {
  // path should start with /api
  if (!path.startsWith('/')) path = '/' + path;
  if (API_BASE) return API_BASE + path;
  return path; // same-origin
}

const activities = [
  {
    id: 1,
    name: '插秧體驗農事活動',
    region: '小半天',
    duration: '一日',
    type: '親子',
    space: '戶外',
    budget: '中',
    stay: '2 小時',
    canEat: '可用餐',
    mealType: '午餐',
    image: 'assets/images/activities/activity-tea.png',
    description: '親手體驗農事流程，適合親子與校外教學。',
    keywords: ['親子', '農事', '茶園']
  },
  {
    id: 2,
    name: '竹編手作體驗',
    region: '大雁',
    duration: '半日',
    type: 'DIY',
    space: '室內',
    budget: '低',
    stay: '1 小時',
    canEat: '可用餐',
    mealType: '點心',
    image: 'assets/images/activities/activity-diy.png',
    description: '用在地素材完成簡單竹編作品，適合短時長活動。',
    keywords: ['DIY', '手作', '竹編']
  },
  {
    id: 3,
    name: '客家文化導覽',
    region: '糯米橋',
    duration: '一日',
    type: '文化導覽',
    space: '混合',
    budget: '中',
    stay: '1.5 小時',
    canEat: '可用餐',
    mealType: '午餐',
    image: 'assets/images/activities/activity-culture.png',
    description: '走讀聚落故事與地景，適合想深入在地文化的旅客。',
    keywords: ['文化', '導覽', '聚落']
  },
  {
    id: 4,
    name: '茶園生態小旅行',
    region: '小半天',
    duration: '一日',
    type: '生態導覽',
    space: '戶外',
    budget: '中',
    stay: '2.5 小時',
    canEat: '不可用餐',
    mealType: '無',
    image: 'assets/images/activities/activity-eco.png',
    description: '結合茶園步道與生態觀察，享受綠意與慢步調。',
    keywords: ['生態', '茶園', '步道']
  },
  {
    id: 5,
    name: '農村餐桌與在地料理',
    region: '糯米橋',
    duration: '半日',
    type: '食農教育',
    space: '室內',
    budget: '高',
    stay: '1.5 小時',
    canEat: '可用餐',
    mealType: '晚餐',
    image: 'assets/images/activities/activity-food.png',
    description: '品嘗在地料理並認識農產來源，適合作為行程收尾。',
    keywords: ['食農教育', '在地料理', '餐桌']
  },
  {
    id: 6,
    name: '親子採果與自然觀察',
    region: '大雁',
    duration: '一日',
    type: '親子',
    space: '戶外',
    budget: '低',
    stay: '2 小時',
    canEat: '不可用餐',
    mealType: '無',
    image: 'assets/images/activities/activity-eco.png',
    description: '適合一日行程中的上午或下午段，動靜皆宜。',
    keywords: ['親子', '自然', '採果']
  }
];

const ASSET_VERSION = Date.now();

function assetUrl(path) {
  return `${path}?v=${ASSET_VERSION}`;
}

const state = {
  keyword: '',
  region: 'all',
  duration: 'all',
  type: 'all',
  stay: 'all',
  space: 'all',
  budget: 'all',
  preset: '親子'
};

const elements = {
  grid: document.getElementById('activityGrid'),
  searchInput: document.getElementById('searchInput'),
  searchButton: document.getElementById('searchButton'),
  currentDateTime: document.getElementById('currentDateTime'),
  itineraryStartTime: document.getElementById('itineraryStartTime'),
  itineraryEndTime: document.getElementById('itineraryEndTime'),
  itineraryStartPoint: document.getElementById('itineraryStartPoint'),
  generateItineraryButton: document.getElementById('generateItineraryButton'),
  itineraryResult: document.getElementById('itineraryResult'),
  regionFilter: document.getElementById('regionFilter'),
  durationFilter: document.getElementById('durationFilter'),
  typeFilter: document.getElementById('typeFilter'),
  stayFilter: document.getElementById('stayFilter'),
  spaceFilter: document.getElementById('spaceFilter'),
  budgetFilter: document.getElementById('budgetFilter'),
  resetFilters: document.getElementById('resetFilters'),
  filterSummary: document.getElementById('filterSummary'),
  assistantInput: document.getElementById('assistantInput'),
  assistantSend: document.getElementById('assistantSend'),
  assistantReply: document.getElementById('assistantReply')
};

function hydrateStaticAssets() {
  document.querySelectorAll('[data-asset]').forEach((element) => {
    const assetPath = element.dataset.asset;
    if (assetPath) {
      element.src = assetUrl(assetPath);
    }
  });
}

function formatDate(value) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}/${month}/${day}`;
}

function updateCurrentDateTime() {
  if (!elements.currentDateTime) {
    return;
  }

  const now = new Date();
  elements.currentDateTime.textContent = now.toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
}

function updateNewsDates() {
  const today = new Date();

  document.querySelectorAll('[data-news-offset]').forEach((element) => {
    const offsetDays = Number.parseInt(element.dataset.newsOffset || '0', 10);
    const displayDate = new Date(today);
    displayDate.setDate(displayDate.getDate() - offsetDays);
    element.textContent = formatDate(displayDate);
  });
}

function setItineraryTimePreset() {
  if (!elements.itineraryStartTime || !elements.itineraryEndTime) {
    return;
  }

  if (state.duration === '半日') {
    elements.itineraryStartTime.value = '09:00';
    elements.itineraryEndTime.value = '13:00';
    return;
  }

  elements.itineraryStartTime.value = '09:00';
  elements.itineraryEndTime.value = '17:00';
}

function buildQueryParams() {
  const params = new URLSearchParams();

  if (state.region !== 'all') params.set('area', state.region);
  if (state.duration !== 'all') params.set('trip_length', state.duration);
  if (state.type !== 'all') params.set('category', state.type);
  if (state.stay !== 'all') params.set('stay_type', state.stay);
  if (state.space !== 'all') params.set('indoor_outdoor', state.space);
  if (state.budget !== 'all') params.set('budget', state.budget);
  if (state.keyword) params.set('keyword', state.keyword);

  return params;
}

async function fetchSpots() {
  const response = await fetch(apiUrl(`/api/spots?${buildQueryParams().toString()}`));
  const payload = await response.json();

  if (!response.ok || !payload.success) {
    throw new Error(payload.error || '無法取得景點資料');
  }

  return payload.data || [];
}

function formatMinutes(minutes) {
  return `${Number(minutes || 0)} 分鐘`;
}

function normalizeText(text) {
  return String(text || '').trim().toLowerCase();
}

function createCard(activity) {
  const template = document.getElementById('activityCardTemplate');
  const clone = template.content.cloneNode(true);

  clone.querySelector('.activity-image').src = assetUrl(activity.image || 'assets/images/activities/activity-tea.png');
  clone.querySelector('.activity-image').alt = activity.name;
  clone.querySelector('.activity-type').textContent = activity.category || activity.activity_type || '';
  clone.querySelector('.activity-region').textContent = activity.area || activity.region || '';
  clone.querySelector('.activity-title').textContent = activity.name;
  clone.querySelector('.activity-desc').textContent = activity.description;
  clone.querySelector('.stay-time').textContent = `建議停留 ${activity.stay_minutes || activity.recommended_stay_minutes || 0} 分鐘`;
  const canDine = activity.can_dine ?? activity.canEat ?? activity.can_eat;
  clone.querySelector('.meal-state').textContent = `${canDine ? '可用餐' : '不可用餐'}｜${activity.meal_type || '無'}`;

  const card = clone.querySelector('.activity-card');
  card.dataset.region = activity.area || activity.region || '';
  card.dataset.duration = activity.trip_length || activity.duration || '';
  card.dataset.type = activity.category || activity.activity_type || '';
  card.dataset.space = activity.indoor_outdoor || activity.space || '';
  card.dataset.budget = activity.budget || activity.budget_level || '';
  card.dataset.search = `${activity.name} ${activity.description} ${activity.keywords || ''}`;

  card.addEventListener('click', () => {
    elements.assistantInput.value = `${activity.area || activity.region || ''} ${activity.trip_length || activity.duration || ''} ${activity.category || activity.activity_type || ''}`.trim();
    elements.assistantInput.focus();
  });

  return clone;
}

function renderActivities(activities) {
  elements.grid.innerHTML = '';

  if (!activities.length) {
    elements.grid.innerHTML = `
      <div class="empty-state">
        <h4>目前沒有符合條件的活動</h4>
        <p>請調整地區、行程長度、活動類型、活動停留時間或關鍵字後再試一次。</p>
      </div>
    `;
  } else {
    activities.forEach((activity) => elements.grid.appendChild(createCard(activity)));
  }

  const summaryParts = [];
  if (state.keyword) summaryParts.push(`關鍵字：${state.keyword}`);
  if (state.region !== 'all') summaryParts.push(`地區：${state.region}`);
  if (state.duration !== 'all') summaryParts.push(`行程長度：${state.duration}`);
  if (state.type !== 'all') summaryParts.push(`活動類型：${state.type}`);
  if (state.stay !== 'all') summaryParts.push(`活動停留時間：${state.stay}`);
  if (state.space !== 'all') summaryParts.push(`室內/戶外：${state.space}`);
  if (state.budget !== 'all') summaryParts.push(`預算：${state.budget}`);

  elements.filterSummary.textContent = summaryParts.length ? `目前條件：${summaryParts.join('、')}` : '目前顯示全部推薦活動';
}

function renderItineraryPlaceholder(title, description) {
  elements.itineraryResult.innerHTML = `
    <div class="result-placeholder">
      <h4>${title}</h4>
      <p>${description}</p>
    </div>
  `;
}

function renderItineraryWarnings(warnings) {
  if (!warnings || !warnings.length) {
    return '';
  }

  return `
    <ul class="warning-list">
      ${warnings.map((warning) => `<li>${warning}</li>`).join('')}
    </ul>
  `;
}

function renderItinerarySummary(summary, isTooRushed) {
  return `
    <div class="itinerary-summary-grid">
      <div class="summary-card"><span>行程長度</span><strong>${summary.trip_length || '-'}</strong></div>
      <div class="summary-card"><span>開始時間</span><strong>${summary.start_time || '-'}</strong></div>
      <div class="summary-card"><span>結束時間</span><strong>${summary.end_time || '-'}</strong></div>
      <div class="summary-card"><span>總停留時間</span><strong>${formatMinutes(summary.total_stay_minutes)}</strong></div>
      <div class="summary-card"><span>總車程時間</span><strong>${formatMinutes(summary.total_travel_minutes)}</strong></div>
      <div class="summary-card"><span>午餐時間</span><strong>${formatMinutes(summary.total_meal_minutes)}</strong></div>
      <div class="summary-card"><span>起點</span><strong>${summary.start_point || '南投車站'}</strong></div>
      <div class="summary-card"><span>是否過趕</span><strong>${isTooRushed ? '是' : '否'}</strong></div>
    </div>
  `;
}

function renderItineraryItems(items) {
    return `
    <div class="itinerary-timeline">
      ${items.map((item) => {
        const source = item.source || item.map_source || (item.type === 'meal' ? 'system' : 'system');
        const sourceLabel = (source === 'google_maps') ? 'Google Maps 預估' : '系統預估';
        const extra = item.distance_text ? `<span class="timeline-chip">${item.distance_text}</span>` : '';
        return `
        <div class="timeline-item ${item.type === 'meal' ? 'meal' : ''}">
          <div class="timeline-label">${item.type === 'meal' ? '午餐' : '景點'}</div>
          <h4>${item.start_time} - ${item.end_time}｜${item.name}</h4>
          <div class="timeline-meta">
            <span class="timeline-chip">停留 ${formatMinutes(item.stay_minutes)}</span>
            <span class="timeline-chip">移動 ${formatMinutes(item.travel_minutes)}</span>
            ${extra}
            <span class="timeline-badge">${sourceLabel}</span>
          </div>
          <p>${item.note || ''}</p>
        </div>
      `}).join('')}
    </div>
  `;
}

function renderItinerary(result) {
  const summary = result.summary || {};
  const warnings = result.warnings || [];
  const items = result.items || [];

  elements.itineraryResult.innerHTML = `
    ${renderItinerarySummary(summary, result.is_too_rushed)}
    ${renderItineraryWarnings(warnings)}
    ${renderItineraryItems(items)}
  `;
}

function renderItineraryError(message, warnings = []) {
  elements.itineraryResult.innerHTML = `
    <div class="result-placeholder">
      <h4>行程產生失敗</h4>
      <p>${message}</p>
    </div>
    ${renderItineraryWarnings(warnings)}
  `;
}

function buildItineraryPayload() {
  return {
    area: state.region === 'all' ? '' : state.region,
    category: state.type === 'all' ? '' : state.type,
    trip_length: state.duration === 'all' ? '一日' : state.duration,
    stay_type: state.stay === 'all' ? '' : state.stay,
    indoor_outdoor: state.space === 'all' ? '' : state.space,
    budget: state.budget === 'all' ? '' : state.budget,
    keyword: state.keyword,
    start_time: elements.itineraryStartTime?.value || '09:00',
    end_time: elements.itineraryEndTime?.value || '17:00',
    start_point: elements.itineraryStartPoint?.value?.trim() || '南投車站'
  };
}

async function generateItinerary() {
  if (!elements.itineraryResult) {
    return;
  }

  elements.itineraryResult.innerHTML = `
    <div class="result-placeholder">
      <h4>行程產生中</h4>
      <p>正在依目前篩選條件與排程規則計算行程。</p>
    </div>
  `;

  try {
    const response = await fetch(apiUrl('/api/itineraries/generate'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(buildItineraryPayload())
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      renderItineraryError(data.message || data.error || '無法產生行程', data.warnings || []);
      return;
    }

    renderItinerary(data);
  } catch (error) {
    renderItineraryError(error.message || '請稍後再試');
  }
}

async function refreshActivities() {
  elements.grid.innerHTML = `
    <div class="empty-state">
      <h4>載入中...</h4>
      <p>正在從 API 讀取推薦活動。</p>
    </div>
  `;

  try {
    const activities = await fetchSpots();
    renderActivities(activities);
  } catch (error) {
    elements.grid.innerHTML = `
      <div class="empty-state">
        <h4>無法載入活動</h4>
        <p>${error.message}</p>
      </div>
    `;
  }
}

function setActiveQuickTag(tagValue) {
  document.querySelectorAll('.tag').forEach((button) => {
    button.classList.toggle('active', button.dataset.quickFilter === tagValue);
  });
}

function getAssistantReply(inputText) {
  const text = normalizeText(inputText);
  if (text.includes('不要戶外')) {
    return '09:00 茶園導覽、11:30 午餐、13:00 手作 DIY、15:30 回程';
  }
  if (text.includes('diy') && text.includes('半日')) {
    return '09:30 竹編體驗、11:00 茶點休息、12:00 結束返程';
  }
  if (text.includes('大雁') && text.includes('咖啡')) {
    return '09:00 大雁稻田散步、11:20 咖啡小屋午茶、13:30 食農教室、15:00 回程';
  }
  return '09:00 活動起點、11:30 午餐、13:00 特色活動、15:30 回程';
}

function updateAssistantReply(inputText) {
  elements.assistantReply.innerHTML = `
    <span class="chat-role">系統</span>
    <p>${getAssistantReply(inputText)}</p>
  `;
}

function bindEvents() {
  elements.searchButton.addEventListener('click', () => {
    state.keyword = elements.searchInput.value.trim();
    refreshActivities();
  });

  elements.searchInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      state.keyword = elements.searchInput.value.trim();
      refreshActivities();
    }
  });

  elements.regionFilter.addEventListener('change', (event) => {
    state.region = event.target.value;
    refreshActivities();
  });

  elements.durationFilter.addEventListener('change', (event) => {
    state.duration = event.target.value;
    setItineraryTimePreset();
    refreshActivities();
  });

  elements.typeFilter.addEventListener('change', (event) => {
    state.type = event.target.value;
    refreshActivities();
  });

  elements.stayFilter.addEventListener('change', (event) => {
    state.stay = event.target.value;
    refreshActivities();
  });

  elements.spaceFilter.addEventListener('change', (event) => {
    state.space = event.target.value;
    refreshActivities();
  });

  elements.budgetFilter.addEventListener('change', (event) => {
    state.budget = event.target.value;
    refreshActivities();
  });

  elements.resetFilters.addEventListener('click', () => {
    state.keyword = '';
    state.region = 'all';
    state.duration = 'all';
    state.type = 'all';
    state.stay = 'all';
    state.space = 'all';
    state.budget = 'all';
    state.preset = '親子';

    elements.searchInput.value = '';
    elements.regionFilter.value = 'all';
    elements.durationFilter.value = 'all';
    elements.typeFilter.value = 'all';
    elements.stayFilter.value = 'all';
    elements.spaceFilter.value = 'all';
    elements.budgetFilter.value = 'all';
    setItineraryTimePreset();

    setActiveQuickTag('親子');
    refreshActivities();
  });

  if (elements.generateItineraryButton) {
    elements.generateItineraryButton.addEventListener('click', generateItinerary);
  }

  document.querySelectorAll('.tag').forEach((button) => {
    button.addEventListener('click', () => {
      state.preset = button.dataset.quickFilter;
      setActiveQuickTag(state.preset);
      state.keyword = button.dataset.quickFilter;
      elements.searchInput.value = button.dataset.quickFilter;
      refreshActivities();
    });
  });

  document.querySelectorAll('.preset-button').forEach((button) => {
    button.addEventListener('click', () => {
      elements.assistantInput.value = button.dataset.preset;
      updateAssistantReply(button.dataset.preset);
    });
  });

  elements.assistantSend.addEventListener('click', () => {
    updateAssistantReply(elements.assistantInput.value);
  });

  elements.assistantInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      updateAssistantReply(elements.assistantInput.value);
    }
  });
}

function init() {
  hydrateStaticAssets();
  updateCurrentDateTime();
  updateNewsDates();
  window.setInterval(updateCurrentDateTime, 60000);
  setItineraryTimePreset();
  renderItineraryPlaceholder('尚未產生行程', '設定條件後，按下「產生行程」即可顯示半日或一日的排程時間表。');
  bindEvents();
  refreshActivities();
}

init();
