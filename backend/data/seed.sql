INSERT OR REPLACE INTO spots (
    id, name, area, category, trip_length, stay_type, stay_minutes,
    budget, indoor_outdoor, can_dine, meal_type, description, image, keywords, is_active
) VALUES
    (1, '小半天親子茶園體驗館', '小半天', '親子', '一日', '中', 120, '中', '戶外', 1, '午餐', '適合親子茶園導覽與輕食。', 'assets/images/activities/activity-tea.png', '茶園,親子,體驗', 1),
    (2, '小半天手作茶點工坊', '小半天', 'DIY', '半日', '短', 60, '低', '室內', 1, '點心', '可安排茶點 DIY 與休息。', 'assets/images/activities/activity-diy.png', 'DIY,茶點,手作', 1),
    (3, '小半天生態步道導覽', '小半天', '生態之旅', '一日', '長', 150, '低', '戶外', 0, '無', '步道景觀與生態導覽。', 'assets/images/activities/activity-eco.png', '步道,生態,導覽', 1),
    (4, '大雁稻田食農教室', '大雁', '食農教育', '一日', '中', 100, '中', '戶外', 1, '午餐', '以食農教育與田野體驗為主。', 'assets/images/activities/activity-food.png', '稻田,食農,教室', 1),
    (5, '大雁田野咖啡小屋', '大雁', '在地美食', '半日', '短', 45, '中', '室內', 1, '點心', '適合點心休息與短暫停留。', 'assets/images/activities/activity-food.png', '咖啡,休息,飲品', 1),
    (6, '大雁戶外自然觀察站', '大雁', '生態之旅', '一日', '長', 150, '低', '戶外', 0, '無', '適合戶外觀察與導覽。', 'assets/images/activities/activity-eco.png', '自然,觀察,戶外', 1),
    (7, '糯米橋古道文化園區', '糯米橋', '文化導覽', '一日', '中', 90, '中', '混合', 1, '午餐', '適合文化走讀與家庭行程。', 'assets/images/activities/activity-culture.png', '文化,古道,親子', 1),
    (8, '糯米橋米食DIY館', '糯米橋', 'DIY', '半日', '短', 70, '低', '室內', 1, '點心', '適合米食手作與簡餐。', 'assets/images/activities/activity-diy.png', '米食,DIY,手作', 1),
    (9, '糯米橋溪畔生態導覽路線', '糯米橋', '生態之旅', '一日', '長', 140, '低', '戶外', 0, '無', '適合自然生態觀察。', 'assets/images/activities/activity-eco.png', '溪畔,生態,導覽', 1),
    (10, '糯米橋鄉村餐桌', '糯米橋', '食農教育', '半日', '中', 80, '中', '室內', 1, '晚餐', '適合安排晚餐或在地料理體驗。', 'assets/images/activities/activity-food.png', '餐桌,在地料理,晚餐', 1),
    (11, '小半天森林導覽步道', '小半天', '生態之旅', '半日', '中', 90, '低', '戶外', 0, '無', '適合上午輕旅行與自然觀察。', 'assets/images/activities/activity-eco.png', '森林,步道,自然', 1),
    (12, '大雁手作米食教室', '大雁', 'DIY', '半日', '短', 65, '低', '室內', 1, '點心', '適合親子體驗與短時段手作。', 'assets/images/activities/activity-diy.png', '米食,手作,親子', 1);
