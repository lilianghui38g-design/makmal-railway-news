import requests
from bs4 import BeautifulSoup
import time
import hashlib
import json
from datetime import datetime
import os
import random
from urllib.parse import urljoin

# -------------------- 配置区域 --------------------
# 信源配置：分为四类
SOURCE_CATEGORIES = {
    "kyrgyz_media": {
        "name": "吉尔吉斯斯坦媒体",
        "urls": [
            "https://24.kg/",
            "https://en.kabar.kg/",
            "https://akipress.org/",
            "https://kaktus.media/",
            "https://kloop.kg/",
        ],
        "selectors": {
            "link_tag": "a",
            "title_attr": "text",
            "link_attr": "href",
            "content_selector": ["article", ".article-content", ".news-detail"]
        }
    },
    "us_media": {
        "name": "美国媒体",
        "urls": [
            "https://www.yahoo.com/news/",
            "https://www.nytimes.com/",
            "https://www.cnn.com/",
            "https://www.foxnews.com/",
            "https://www.msn.com/",
            "https://www.wsj.com/",
            "https://www.washingtonpost.com/",
            "https://www.latimes.com/",
        ],
        "selectors": {
            "link_tag": "a",
            "title_attr": "text",
            "link_attr": "href",
            "content_selector": ["article", ".story-content", ".article-body"]
        }
    },
    "companies": {
        "name": "相关公司/机构",
        "urls": [
            "https://allamericanrailgroup.com/",  # 实际需核实
            "https://www.railway.gov.kg/",  # 吉尔吉斯铁路官网
            "http://invest.gov.kg/",  # 国家投资署
        ],
        "selectors": {
            "link_tag": "a",
            "title_attr": "text",
            "link_attr": "href",
            "content_selector": ["article", ".content", ".node__content"]
        }
    },
    "think_tanks": {
        "name": "国际智库",
        "urls": [
            "https://carnegieendowment.org/",
            "https://www.atlanticcouncil.org/",
            "https://www.rand.org/",
            "https://www.csis.org/",
            "https://www.chathamhouse.org/",
        ],
        "selectors": {
            "link_tag": "a",
            "title_attr": "text",
            "link_attr": "href",
            "content_selector": ["article", ".publication-content", ".research-output"]
        }
    }
}

# 搜索关键词 (多语言，覆盖四类信源可能出现的表述)
KEYWORDS = [
    # 项目名称
    "Makmal-Karakol", "Makmal—Karakol", "Makmal Karakol",
    "Макмал-Каракол", "Макмал Каракол",
    "马克马尔-卡拉科尔",
    # 公司/机构
    "All American Rail Group", "Kyrgyz Temir Zholu", "National Investment Agency",
    # 相关术语
    "Trans-Eurasian route", "public-private partnership", "PPP railway",
    "трансевразийский маршрут", "государственно-частное партнерство",
    # 地缘政治相关
    "US railway Kyrgyzstan", "American investment Kyrgyzstan",
    "competition BRI", "China Kyrgyzstan railway"
]

# 数据存储文件
DATA_FILE = "makmal_karakol_news.json"
# 抓取间隔 (秒) - 建议设为6-12小时避免被封
CRAWL_INTERVAL = 6 * 3600  # 6小时
REQUEST_DELAY = 2  # 请求间隔延迟(秒)，避免过快访问

# User-Agent轮换
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
]
# -------------------- 功能函数 --------------------

def load_previous_data():
    """加载已抓取的数据，用于去重"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                # 确保数据结构兼容
                if isinstance(data, list):
                    return data
                else:
                    return []
            except:
                return []
    return []

def save_data(data):
    """保存数据到文件"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_article_id(url, title):
    """根据URL和标题生成唯一ID，用于去重"""
    unique_string = f"{url}{title}"
    return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

def fetch_page(url, category_name):
    """带重试和延迟的页面获取"""
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        # 礼貌性延迟
        time.sleep(REQUEST_DELAY + random.uniform(0, 1))
        
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            return response.text
        else:
            print(f"获取失败 {url} - 状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"请求异常 {url}: {e}")
        return None

def scan_website(base_url, category_name, config, existing_ids):
    """扫描单个网站并提取相关文章"""
    new_articles = []
    
    print(f"正在扫描 [{category_name}] {base_url}")
    
    html = fetch_page(base_url, category_name)
    if not html:
        return []
    
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # 查找所有可能的新闻链接
        all_links = soup.find_all(config.get('link_tag', 'a'), href=True)
        
        for link in all_links[:50]:  # 限制每页最多处理50条链接
            title = link.get_text(strip=True)
            href = link['href']
            
            # 跳过空标题或过短的标题
            if len(title) < 8:
                continue
            
            # 处理相对URL
            if href.startswith('/'):
                full_url = urljoin(base_url, href)
            elif href.startswith('http'):
                full_url = href
            else:
                # 尝试拼接
                full_url = urljoin(base_url, href)
            
            # 关键词过滤：检查标题或URL中是否包含关键词
            matched = False
            matched_keyword = None
            text_to_check = (title + " " + full_url).lower()
            
            for keyword in KEYWORDS:
                if keyword.lower() in text_to_check:
                    matched = True
                    matched_keyword = keyword
                    break
            
            if matched:
                article_id = generate_article_id(full_url, title)
                if article_id not in existing_ids:
                    print(f"  → 发现新报道: {title[:60]}... (关键词: {matched_keyword})")
                    
                    article_data = {
                        "id": article_id,
                        "title": title,
                        "url": full_url,
                        "source_domain": base_url,
                        "source_category": category_name,
                        "source_category_name": SOURCE_CATEGORIES[category_name]["name"],
                        "matched_keyword": matched_keyword,
                        "discovered_at": datetime.now().isoformat(),
                    }
                    new_articles.append(article_data)
                    existing_ids.add(article_id)
    
    except Exception as e:
        print(f"解析 {base_url} 时出错: {e}")
    
    return new_articles

def send_notification(new_articles):
    """发送通知（可选功能：邮件、Slack、钉钉等）"""
    # 这里可以集成通知服务
    if new_articles:
        categories = {}
        for article in new_articles:
            cat = article['source_category_name']
            categories[cat] = categories.get(cat, 0) + 1
        
        print("\n" + "="*50)
        print(f"✅ 发现 {len(new_articles)} 篇新报道")
        for cat, count in categories.items():
            print(f"  {cat}: {count}篇")
        print("="*50)

# -------------------- 主循环 --------------------
def main():
    print("="*60)
    print("马克马尔-卡拉科尔铁路新闻爬虫 (四类信源版)")
    print(f"启动时间: {datetime.now()}")
    print("信源分类: 吉尔吉斯媒体 | 美国媒体 | 公司机构 | 国际智库")
    print("="*60)
    
    # 加载已有数据
    all_articles = load_previous_data()
    existing_ids = set(article['id'] for article in all_articles)
    
    print(f"已加载历史数据: {len(all_articles)} 篇")
    
    while True:
        print(f"\n--- 抓轮开始: {datetime.now()} ---")
        newly_found_total = []
        
        # 按类别依次扫描
        for category_key, category_config in SOURCE_CATEGORIES.items():
            print(f"\n>> 类别: {category_config['name']}")
            
            for url in category_config['urls']:
                found = scan_website(url, category_key, category_config['selectors'], existing_ids)
                newly_found_total.extend(found)
        
        # 保存新数据
        if newly_found_total:
            all_articles.extend(newly_found_total)
            save_data(all_articles)
            send_notification(newly_found_total)
        else:
            print("\n本轮未发现新报道")
        
        # 统计各信源累计数据
        print(f"\n📊 累计报道总数: {len(all_articles)} 篇")
        source_stats = {}
        for article in all_articles:
            cat = article.get('source_category_name', '其他')
            source_stats[cat] = source_stats.get(cat, 0) + 1
        for cat, count in source_stats.items():
            print(f"  {cat}: {count}篇")
        
        # 等待下一轮
        next_run = datetime.fromtimestamp(time.time() + CRAWL_INTERVAL)
        print(f"\n⏳ 等待 {CRAWL_INTERVAL/3600:.1f} 小时后进行下一轮 (下次运行: {next_run.strftime('%Y-%m-%d %H:%M:%S')})")
        time.sleep(CRAWL_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n爬虫已手动停止")
        # 退出前保存数据
        if 'all_articles' in locals():
            save_data(all_articles)
            print("数据已保存")
