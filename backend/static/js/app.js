const spotListEl = document.getElementById('spot-list');
const spotCountEl = document.getElementById('spot-count');
const itineraryResultEl = document.getElementById('itinerary-result');
const assistantResultEl = document.getElementById('assistant-result');
const lineResultEl = document.getElementById('line-result');

function formToQueryString(form) {
  const data = new FormData(form);
  const params = new URLSearchParams();
  for (const [key, value] of data.entries()) {
    if (value !== '') {
      params.append(key, value);
    }
  }
  return params.toString();
}

function renderSpots(spots) {
  spotCountEl.textContent = `${spots.length} 筆`;
  if (!spots.length) {
    spotListEl.innerHTML = '<p>沒有符合條件的景點。</p>';
    return;
  }

  spotListEl.innerHTML = spots.map((spot) => `
    <article class="spot-card">
      <h3>${spot.name}</h3>
      <p>${spot.region}｜${spot.address}</p>
      <p>${spot.description || ''}</p>
      <div class="badge-row">
        <span class="badge">${spot.activity_type}</span>
        <span class="badge">停留 ${spot.recommended_stay_minutes} 分鐘</span>
        <span class="badge">${spot.stay_level}</span>
        <span class="badge">${spot.budget_level}</span>
        <span class="badge">${spot.indoor_outdoor}</span>
        <span class="badge">${spot.can_eat ? spot.meal_type : '不可用餐'}</span>
      </div>
    </article>
  `).join('');
}

async function loadSpots(queryString = '') {
  const response = await fetch(`/api/spots${queryString ? `?${queryString}` : ''}`);
  const data = await response.json();
  renderSpots(data.data || []);
}

function renderItinerary(result) {
  const items = result.items || [];
  const rushText = result.is_rushed ? `是，原因：\n- ${result.rush_reason.join('\n- ')}` : '否';
  itineraryResultEl.innerHTML = `
    <div class="timeline">
      <div class="timeline-item"><strong>開始：</strong>${result.start_time}</div>
      <div class="timeline-item"><strong>結束：</strong>${result.end_time}</div>
      <div class="timeline-item"><strong>總車程：</strong>${result.total_travel_minutes} 分鐘</div>
      <div class="timeline-item"><strong>總停留：</strong>${result.total_stay_minutes} 分鐘</div>
      <div class="timeline-item"><strong>是否過趕：</strong>${rushText}</div>
      ${items.map((item) => `
        <div class="timeline-item">
          <strong>${item.start_time} - ${item.end_time}</strong><br>
          ${item.title}｜${item.item_type}｜停留 ${item.stay_minutes} 分鐘｜車程 ${item.travel_minutes} 分鐘
        </div>
      `).join('')}
    </div>
  `;
}

function renderAssistantResult(result) {
  if (!assistantResultEl) {
    return;
  }

  if (!result || !result.success) {
    assistantResultEl.textContent = result?.error || '助理回覆失敗。';
    return;
  }

  assistantResultEl.textContent = result.text || '沒有回覆內容。';
}

document.getElementById('filter-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  await loadSpots(formToQueryString(event.currentTarget));
});

document.getElementById('itinerary-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const filterForm = document.getElementById('filter-form');
  const payload = Object.fromEntries(new FormData(filterForm).entries());

  for (const [key, value] of formData.entries()) {
    payload[key] = value;
  }

  const response = await fetch('/api/itineraries/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  renderItinerary(data);
});

document.getElementById('assistant-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const preferences = formData.getAll('preferences');

  const payload = {
    message: formData.get('message') || '',
    origin: formData.get('origin') || '',
    date: formData.get('date') || '',
    start_time: formData.get('start_time') || '',
    end_date: formData.get('end_date') || '',
    end_time: formData.get('end_time') || '',
    trip_length: formData.get('trip_length') || '',
    area: formData.get('area') || '',
    preferences,
  };

  const response = await fetch('/api/assistant/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  renderAssistantResult(data);
});

document.getElementById('line-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const response = await fetch('/api/line/webhook', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: formData.get('line_text') }),
  });
  const data = await response.json();
  lineResultEl.textContent = JSON.stringify(data, null, 2);
});

loadSpots();
