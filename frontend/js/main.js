// API base selection
// If window.__API_BASE__ is set (via hosting or a build), use that.
// If running on localhost, default to local Flask backend.
const _API_BASE_RAW = (window.__API_BASE__ !== undefined) ? window.__API_BASE__ : (location.hostname === 'localhost' || location.hostname === '127.0.0.1' ? 'http://127.0.0.1:5004' : '');
const API_BASE = _API_BASE_RAW ? _API_BASE_RAW.replace(/\/$/, '') : '';

if (window.marked && window.marked.setOptions) {
  window.marked.setOptions({ breaks: true });
}

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
  latestNewsList: document.getElementById('latestNewsList'),
  tripOrigin: document.getElementById('tripOrigin'),
  tripStartDate: document.getElementById('tripStartDate'),
  tripStartTime: document.getElementById('tripStartTime'),
  tripEndDate: document.getElementById('tripEndDate'),
  tripEndTime: document.getElementById('tripEndTime'),
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

// latest news pagination elements & state
elements.newsPrev = document.getElementById('newsPrev');
elements.newsNext = document.getElementById('newsNext');
elements.newsDots = document.getElementById('newsDots');

const latestNews = {
  items: [],
  pageSize: 3,
  pageIndex: 0
};

// recommendation pagination elements
elements.recommendPrev = document.getElementById('recommendPrev');
elements.recommendNext = document.getElementById('recommendNext');
elements.recommendDots = document.getElementById('recommendDots');

const recommend = {
  items: [],
  pageSize: 6,
  pageIndex: 0
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

function formatNewsDate(value) {
  if (!value) {
    return '日期未知';
  }

  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return '日期未知';
  }

  return parsedDate.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
}

function truncateText(text, maxLength = 90) {
  const cleanText = String(text || '').replace(/\s+/g, ' ').trim();
  if (cleanText.length <= maxLength) {
    return cleanText;
  }

  return `${cleanText.slice(0, maxLength)}…`;
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderNewsItems(items) {
  if (!elements.latestNewsList) {
    return;
  }

  if (!items.length) {
    elements.latestNewsList.innerHTML = `
      <li class="news-loading">
        <span class="news-date">無資料</span>
        <p>目前沒有可顯示的最新消息。</p>
      </li>
    `;
    return;
  }

  elements.latestNewsList.innerHTML = items.map((item) => {
    const title = escapeHtml(truncateText(item.title, 70));
    const summary = escapeHtml(truncateText(item.summary || '點擊查看完整內容。', 110));
    const publishedAt = escapeHtml(formatNewsDate(item.published_at || item.publishedAt));
    const link = escapeHtml(item.link || '#');

    return `
      <li>
        <span class="news-date">${publishedAt}</span>
        <a class="news-title" href="${link}" target="_blank" rel="noreferrer noopener">${title}</a>
        <p class="news-summary">${summary}</p>
      </li>
    `;
  }).join('');
}

function renderNewsPage() {
  const items = latestNews.items || [];
  const total = items.length;
  const pages = Math.max(1, Math.ceil(total / latestNews.pageSize));
  if (latestNews.pageIndex >= pages) latestNews.pageIndex = pages - 1;

  const start = latestNews.pageIndex * latestNews.pageSize;
  const end = start + latestNews.pageSize;
  const pageItems = items.slice(start, end);

  if (!elements.latestNewsList) return;
  if (!pageItems.length) {
    elements.latestNewsList.innerHTML = `
      <li class="news-loading">
        <span class="news-date">無資料</span>
        <p>目前沒有可顯示的最新消息。</p>
      </li>
    `;
  } else {
    elements.latestNewsList.innerHTML = pageItems.map((item) => {
      const title = escapeHtml(truncateText(item.title, 70));
      const summary = escapeHtml(truncateText(item.summary || '點擊查看完整內容。', 110));
      const publishedAt = escapeHtml(formatNewsDate(item.published_at || item.publishedAt));
      const link = escapeHtml(item.link || '#');

      return `
        <li>
          <span class="news-date">${publishedAt}</span>
          <a class="news-title" href="${link}" target="_blank" rel="noreferrer noopener">${title}</a>
          <p class="news-summary">${summary}</p>
        </li>
      `;
    }).join('');
  }

  // update controls
  updateNewsControls(pages);
}

function updateNewsControls(pages) {
  if (elements.newsPrev) elements.newsPrev.disabled = latestNews.pageIndex <= 0;
  if (elements.newsNext) elements.newsNext.disabled = latestNews.pageIndex >= pages - 1;

  if (!elements.newsDots) return;
  elements.newsDots.innerHTML = '';
  for (let i = 0; i < pages; i++) {
    const dot = document.createElement('button');
    dot.className = 'page-dot' + (i === latestNews.pageIndex ? ' active' : '');
    dot.setAttribute('aria-label', `第 ${i + 1} 頁`);
    dot.type = 'button';
    dot.addEventListener('click', () => {
      latestNews.pageIndex = i;
      renderNewsPage();
    });
    elements.newsDots.appendChild(dot);
  }
}

async function fetchLatestNews() {
  // fetch up to 30 items (API caps at 30); we'll paginate client-side
  const response = await fetch(apiUrl('/api/news/latest?limit=30'));
  const payload = await response.json();

  if (!response.ok || !payload.success) {
    throw new Error(payload.error || '無法取得最新消息');
  }

  return payload.data || [];
}

async function refreshLatestNews() {
  if (!elements.latestNewsList) {
    return;
  }

  elements.latestNewsList.innerHTML = `
    <li class="news-loading">
      <span class="news-date">載入中...</span>
      <p>正在抓取南投旅遊網最新消息。</p>
    </li>
  `;

  try {
    const newsItems = await fetchLatestNews();
    latestNews.items = newsItems || [];
    latestNews.pageIndex = 0;
    renderNewsPage();
  } catch (error) {
    elements.latestNewsList.innerHTML = `
      <li class="news-loading">
        <span class="news-date">載入失敗</span>
        <p>${escapeHtml(error.message || '請稍後再試')}</p>
      </li>
    `;
  }
}

async function fetchFilters() {
  try {
    const res = await fetch(apiUrl('/api/filters'));
    const payload = await res.json();
    if (!res.ok || !payload.success) return;
    const data = payload.data || {};

    function populate(selectEl, items) {
      if (!selectEl) return;
      // keep "all" as first option
      selectEl.innerHTML = '';
      const allOpt = document.createElement('option');
      allOpt.value = 'all';
      allOpt.textContent = '全部';
      selectEl.appendChild(allOpt);
      (items || []).forEach((it) => {
        const opt = document.createElement('option');
        opt.value = it;
        opt.textContent = it;
        selectEl.appendChild(opt);
      });
    }

    populate(elements.regionFilter, data.areas);
    populate(elements.durationFilter, data.trip_lengths);
    populate(elements.typeFilter, data.categories);
    populate(elements.stayFilter, data.stay_types);
    populate(elements.spaceFilter, data.indoor_outdoor);
    populate(elements.budgetFilter, data.budgets);
  } catch (e) {
    // ignore, keep existing static options
    console.warn('fetchFilters failed', e);
  }
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

    // category badge
    const badge = clone.querySelector('.category-badge');
    if (badge) {
      badge.textContent = activity.category || activity.activity_type || '';
    }

    // keywords
    const kwContainer = clone.querySelector('.activity-keywords');
    if (kwContainer) {
      kwContainer.innerHTML = '';
      const kws = (activity.keywords || '').split(',').map((k) => k.trim()).filter(Boolean).slice(0,4);
      kws.forEach((k) => {
        const chip = document.createElement('span');
        chip.className = 'activity-tag kw';
        chip.textContent = k;
        kwContainer.appendChild(chip);
      });
    }

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

function renderRecommendPage() {
  const items = recommend.items || [];
  const total = items.length;
  const pages = Math.max(1, Math.ceil(total / recommend.pageSize));
  if (recommend.pageIndex >= pages) recommend.pageIndex = pages - 1;

  const start = recommend.pageIndex * recommend.pageSize;
  const end = start + recommend.pageSize;
  const pageItems = items.slice(start, end);

  elements.grid.innerHTML = '';
  if (!pageItems.length) {
    elements.grid.innerHTML = `
      <div class="empty-state">
        <h4>目前沒有符合條件的活動</h4>
        <p>請調整地區、行程長度、活動類型、活動停留時間或關鍵字後再試一次。</p>
      </div>
    `;
  } else {
    pageItems.forEach((activity) => elements.grid.appendChild(createCard(activity)));
  }

  // update controls
  updateRecommendControls(pages);
}

function updateRecommendControls(pages) {
  // prev/next
  if (elements.recommendPrev) elements.recommendPrev.disabled = recommend.pageIndex <= 0;
  if (elements.recommendNext) elements.recommendNext.disabled = recommend.pageIndex >= pages - 1;

  // dots
  if (!elements.recommendDots) return;
  elements.recommendDots.innerHTML = '';
  for (let i = 0; i < pages; i++) {
    const dot = document.createElement('button');
    dot.className = 'page-dot' + (i === recommend.pageIndex ? ' active' : '');
    dot.setAttribute('aria-label', `第 ${i + 1} 頁`);
    dot.type = 'button';
    dot.addEventListener('click', () => {
      recommend.pageIndex = i;
      renderRecommendPage();
    });
    elements.recommendDots.appendChild(dot);
  }
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
        const source = item.source || item.route_source || '系統估算';
        const sourceLabel = source || '系統估算';
        const routeText = item.duration_text || '目前使用系統估算車程';
        const travelFrom = item.travel_from ? `${item.travel_from} → ${item.name || ''}` : '';
        const addressText = item.address ? `<p class="timeline-address">地址：${item.address}</p>` : '';
        const descriptionText = item.description ? `<p class="timeline-description">活動說明：${item.description}</p>` : '';
        return `
        <div class="timeline-item ${item.type === 'meal' ? 'meal' : ''}">
          <div class="timeline-label">${item.type === 'meal' ? (item.name || '午餐／休息') : '景點'}</div>
          <h4>${item.start_time} - ${item.end_time}｜${item.name}</h4>
          ${addressText}
          <div class="timeline-meta">
            <span class="timeline-chip">停留 ${formatMinutes(item.stay_minutes)}</span>
            <span class="timeline-chip">車程 ${routeText}</span>
            ${travelFrom ? `<span class="timeline-chip">${travelFrom}</span>` : ''}
            <span class="timeline-badge">${sourceLabel}</span>
          </div>
          ${descriptionText}
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
  // compose start/end datetime strings in format YYYY-MM-DD HH:MM
  const today = new Date();
  const pad = (v) => String(v).padStart(2, '0');
  const defaultDate = `${today.getFullYear()}-${pad(today.getMonth()+1)}-${pad(today.getDate())}`;
  const startDate = elements.tripStartDate?.value || defaultDate;
  const endDate = elements.tripEndDate?.value || startDate;
  const startTime = elements.tripStartTime?.value || '09:00';
  const endTime = elements.tripEndTime?.value || '17:00';
  const startDatetime = `${startDate} ${startTime}`;
  const endDatetime = `${endDate} ${endTime}`;

  return {
    area: state.region === 'all' ? '' : state.region,
    category: state.type === 'all' ? '' : state.type,
    trip_length: state.duration === 'all' ? '' : state.duration,
    stay_type: state.stay === 'all' ? '' : state.stay,
    indoor_outdoor: state.space === 'all' ? '' : state.space,
    budget: state.budget === 'all' ? '' : state.budget,
    keyword: state.keyword,
    start_datetime: startDatetime,
    end_datetime: endDatetime,
    itinerary_length: state.duration === '半日' ? 'half_day' : 'full_day',
    // keep backward-compatible start_point and optional origin coords
    start_point: elements.tripOrigin?.value?.trim() || '',
    origin_latitude: elements.originLatitude?.value || undefined,
    origin_longitude: elements.originLongitude?.value || undefined,
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
    recommend.items = activities || [];
    recommend.pageIndex = 0;
    renderRecommendPage();
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

function bindSidebarNavigation() {
  document.querySelectorAll('.nav-item').forEach((link) => {
    link.addEventListener('click', (event) => {
      const href = link.getAttribute('href');
      const sectionId = href;
      const section = sectionId ? document.querySelector(sectionId) : null;
      if (!section) {
        return;
      }

      event.preventDefault();
      section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
}

function getAssistantReplyDemo(inputText) {
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

function renderAssistantResponse(role, response, sourceLabel) {
  const responseText = response && typeof response === 'object' ? (response.text || '') : String(response || '');
  const renderedMarkdown = window.marked ? window.marked.parse(responseText) : escapeHtml(responseText).replace(/\n/g, '<br>');

  elements.assistantReply.innerHTML = `
    <span class="chat-role">${escapeHtml(role)}</span>
    <div class="assistant-markdown">${renderedMarkdown}</div>
    ${sourceLabel ? `<div class="assistant-source">來源：${escapeHtml(sourceLabel)}</div>` : ''}
  `;
}

function setAssistantLoading(isLoading) {
  if (isLoading) {
    elements.assistantReply.innerHTML = `
      <span class="chat-role">系統</span>
      <p>處理中…</p>
    `;
    elements.assistantSend.disabled = true;
  } else {
    elements.assistantSend.disabled = false;
  }
}

async function callAssistantApi(payload) {
  try {
    const resp = await fetch(apiUrl('/api/assistant/message'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    if (!resp.ok || !data.success) {
      throw new Error(data.error || 'Assistant API error');
    }
    // attempt to extract text
    const text = data.text || (data.raw && data.raw.candidates && data.raw.candidates[0] && (data.raw.candidates[0].output || data.raw.candidates[0].content)) || '';
    return { success: true, text: text, raw: data.raw };
  } catch (e) {
    return { success: false, error: e.message };
  }
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

  elements.assistantSend.addEventListener('click', async () => {
    const message = elements.assistantInput.value || '';
    const origin = elements.tripOrigin?.value?.trim() || null;
    const startDate = elements.tripStartDate?.value || null;
    const startTime = elements.tripStartTime?.value || null;
    const endDate = elements.tripEndDate?.value || null;
    const endTime = elements.tripEndTime?.value || null;
    const hasTripForm = origin || startDate || startTime || endDate || endTime;

    if (!message.trim() && !hasTripForm) {
      renderAssistantResponse('系統', { text: '請輸入需求或填寫行程條件' }, '本地檢查');
      return;
    }

    const finalMessage = message.trim() || '請依照以上出發資訊安排合適行程';

    const payload = {
      message: finalMessage,
      origin,
      date: startDate,
      start_date: startDate,
      start_time: startTime || '09:00',
      end_date: endDate,
      end_time: endTime,
    };

    setAssistantLoading(true);
    const res = await callAssistantApi(payload);
    setAssistantLoading(false);
    if (res.success) {
      renderAssistantResponse('系統', { text: res.text || getAssistantReplyDemo(finalMessage) }, 'Gemini');
    } else {
      // fallback to demo behavior
      renderAssistantResponse('系統（離線模式）', { text: getAssistantReplyDemo(finalMessage) }, '本地範例');
    }
  });

  elements.assistantInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      elements.assistantSend.click();
    }
  });

  // pagination prev/next handlers
  if (elements.recommendPrev) elements.recommendPrev.addEventListener('click', () => {
    if (recommend.pageIndex > 0) {
      recommend.pageIndex--;
      renderRecommendPage();
    }
  });

  if (elements.recommendNext) elements.recommendNext.addEventListener('click', () => {
    const pages = Math.max(1, Math.ceil((recommend.items || []).length / recommend.pageSize));
    if (recommend.pageIndex < pages - 1) {
      recommend.pageIndex++;
      renderRecommendPage();
    }
  });

  // news pagination handlers
  if (elements.newsPrev) elements.newsPrev.addEventListener('click', () => {
    if (latestNews.pageIndex > 0) {
      latestNews.pageIndex--;
      renderNewsPage();
    }
  });

  if (elements.newsNext) elements.newsNext.addEventListener('click', () => {
    const pages = Math.max(1, Math.ceil((latestNews.items || []).length / latestNews.pageSize));
    if (latestNews.pageIndex < pages - 1) {
      latestNews.pageIndex++;
      renderNewsPage();
    }
  });
}

function init() {
  hydrateStaticAssets();
  updateCurrentDateTime();
  bindSidebarNavigation();
  refreshLatestNews();
  fetchFilters();
  // initialize itinerary date inputs to today by default
  const today = new Date();
  const pad = (v) => String(v).padStart(2, '0');
  const defaultDate = `${today.getFullYear()}-${pad(today.getMonth()+1)}-${pad(today.getDate())}`;
  if (elements.itineraryStartDate && !elements.itineraryStartDate.value) elements.itineraryStartDate.value = defaultDate;
  if (elements.itineraryEndDate && !elements.itineraryEndDate.value) elements.itineraryEndDate.value = defaultDate;
  window.setInterval(updateCurrentDateTime, 60000);
  window.setInterval(refreshLatestNews, 60 * 60 * 1000 * 12);
  setItineraryTimePreset();
  renderItineraryPlaceholder('尚未產生行程', '設定條件後，按下「產生行程」即可顯示半日或一日的排程時間表。');
  bindEvents();
  refreshActivities();
}

init();
