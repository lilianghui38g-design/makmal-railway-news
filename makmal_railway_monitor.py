import streamlit as st
import requests
from bs4 import BeautifulSoup
import feedparser
import pandas as pd
from datetime import datetime, timedelta
import time
import hashlib
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

# 页面配置
st.set_page_config(
    page_title="马克马尔—卡拉科尔铁路新闻监控",
    page_icon="🚂",
    layout="wide"
)

# 标题
st.title("🚂 马克马尔—卡拉科尔铁路实时新闻监控")
st.markdown("监控来源：吉尔吉斯媒体、美国媒体、相关公司、国际智库")

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 监控设置")
    
    # 关键词设置
    st.subheader("关键词")
    default_keywords = """Makmal-Karakol
Макмал-Каракол
马克马尔-卡拉科尔
All American Rail Group
Kyrgyz Temir Zholu
National Investment Agency
PPP railway
Trans-Eurasian route"""
    
    keywords_text = st.text_area("输入关键词（每行一个）", default_keywords, height=150)
    keywords = [k.strip() for k in keywords_text.split('\n') if k.strip()]
    
    # 时间范围
    days_back = st.slider("回溯天数", 1, 30, 7)
    
    # 刷新按钮
    if st.button("🔄 手动刷新"):
        st.session_state['last_refresh'] = datetime.now()
        st.rerun()
    
    st.info("数据每6小时自动更新一次，也可以手动刷新")

# 定义信源
@st.cache_data(ttl=21600)  # 缓存6小时
def load_sources():
    """定义所有监控信源"""
    sources = {
        "吉尔吉斯媒体": {
            "icon": "🇰🇬",
            "urls": [
                {
                    "name": "卡巴尔通讯社",
                    "url": "https://kabar.kg/",
                    "rss": "https://kabar.kg/rss/",
                    "type": "rss"
                },
                {
                    "name": "24.kg",
                    "url": "https://24.kg/",
                    "rss": "https://24.kg/rss/",
                    "type": "rss"
                },
                {
                    "name": "AKIpress",
                    "url": "https://akipress.com/",
                    "rss": "https://akipress.com/rss/",
                    "type": "rss"
                }
            ]
        },
        "美国媒体": {
            "icon": "🇺🇸",
            "urls": [
                {
                    "name": "Yahoo News",
                    "url": "https://news.yahoo.com/",
                    "rss": "https://www.yahoo.com/news/rss",
                    "type": "rss"
                },
                {
                    "name": "CNN",
                    "url": "https://www.cnn.com/",
                    "rss": "http://rss.cnn.com/rss/cnn_topstories.rss",
                    "type": "rss"
                },
                {
                    "name": "Fox News",
                    "url": "https://www.foxnews.com/",
                    "rss": "https://moxie.foxnews.com/google-publisher/world.xml",
                    "type": "rss"
                }
            ]
        },
        "相关公司/机构": {
            "icon": "🏢",
            "urls": [
                {
                    "name": "吉尔吉斯国家铁路公司",
                    "url": "http://www.railway.gov.kg/",
                    "type": "web",
                    "check_url": "http://www.railway.gov.kg/"
                },
                {
                    "name": "吉尔吉斯国家投资署",
                    "url": "http://invest.gov.kg/",
                    "type": "web",
                    "check_url": "http://invest.gov.kg/"
                },
                {
                    "name": "All American Rail Group",
                    "url": "https://allamericanrailgroup.com/",
                    "type": "web",
                    "check_url": "https://allamericanrailgroup.com/"
                }
            ]
        },
        "国际智库": {
            "icon": "📚",
            "urls": [
                {
                    "name": "CSIS",
                    "url": "https://www.csis.org/",
                    "rss": "https://www.csis.org/rss.xml",
                    "type": "rss"
                },
                {
                    "name": "Carnegie Endowment",
                    "url": "https://carnegieendowment.org/",
                    "rss": "https://carnegieendowment.org/rss/",
                    "type": "rss"
                },
                {
                    "name": "RAND Corporation",
                    "url": "https://www.rand.org/",
                    "rss": "https://www.rand.org/topics/rss.xml",
                    "type": "rss"
                },
                {
                    "name": "Atlantic Council",
                    "url": "https://www.atlanticcouncil.org/",
                    "rss": "https://www.atlanticcouncil.org/feed/",
                    "type": "rss"
                }
            ]
        }
    }
    return sources

# RSS解析函数
def parse_rss(feed_url, source_name, keywords, days_back):
    """解析RSS源并过滤关键词"""
    articles = []
    try:
        feed = feedparser.parse(feed_url)
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        for entry in feed.entries[:50]:  # 限制每源最多50条
            # 解析发布时间
            if hasattr(entry, 'published_parsed'):
                pub_date = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed'):
                pub_date = datetime(*entry.updated_parsed[:6])
            else:
                pub_date = datetime.now()
            
            if pub_date < cutoff_date:
                continue
            
            # 检查标题和摘要是否包含关键词
            title = entry.get('title', '')
            summary = entry.get('summary', '')
            full_text = (title + " " + summary).lower()
            
            matched_keywords = []
            for keyword in keywords:
                if keyword.lower() in full_text:
                    matched_keywords.append(keyword)
            
            if matched_keywords:
                articles.append({
                    'title': title,
                    'url': entry.get('link', ''),
                    'source': source_name,
                    'source_type': 'RSS',
                    'published': pub_date,
                    'matched_keywords': ', '.join(matched_keywords),
                    'snippet': summary[:200] + '...' if summary else title
                })
    except Exception as e:
        st.error(f"解析 {feed_url} 时出错: {e}")
    
    return articles

# 网页爬取函数（用于没有RSS的网站）
def check_website(url, source_name, keywords):
    """检查网站页面是否包含关键词"""
    articles = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找所有链接
        for link in soup.find_all('a', href=True):
            title = link.get_text(strip=True)
            href = link['href']
            
            if len(title) < 10:
                continue
            
            # 构建完整URL
            if href.startswith('/'):
                full_url = urlparse(url).scheme + "://" + urlparse(url).netloc + href
            elif href.startswith('http'):
                full_url = href
            else:
                continue
            
            # 检查标题是否包含关键词
            matched_keywords = []
            for keyword in keywords:
                if keyword.lower() in title.lower():
                    matched_keywords.append(keyword)
            
            if matched_keywords:
                articles.append({
                    'title': title,
                    'url': full_url,
                    'source': source_name,
                    'source_type': '网页',
                    'published': datetime.now(),
                    'matched_keywords': ', '.join(matched_keywords),
                    'snippet': title
                })
    except Exception as e:
        st.error(f"检查 {url} 时出错: {e}")
    
    return articles[:20]  # 限制数量

# 主函数：获取所有新闻
@st.cache_data(ttl=21600)
def fetch_all_news(keywords, days_back):
    """获取所有源的最新新闻"""
    all_articles = []
    sources = load_sources()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_sources = sum(len(category['urls']) for category in sources.values())
    current = 0
    
    for category_name, category_data in sources.items():
        for source in category_data['urls']:
            status_text.text(f"正在检查: {source['name']}...")
            
            if source['type'] == 'rss' and 'rss' in source:
                articles = parse_rss(source['rss'], source['name'], keywords, days_back)
                all_articles.extend(articles)
            elif source['type'] == 'web':
                articles = check_website(source['check_url'], source['name'], keywords)
                all_articles.extend(articles)
            
            current += 1
            progress_bar.progress(current / total_sources)
            time.sleep(0.5)  # 礼貌性延迟
    
    progress_bar.empty()
    status_text.empty()
    
    # 按发布时间排序
    all_articles.sort(key=lambda x: x['published'], reverse=True)
    
    return all_articles

# 主界面
def main():
    # 初始化session state
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now()
    
    # 显示上次更新时间
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.info(f"📅 最后更新: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
    with col3:
        if st.button("🔄 立即更新"):
            st.cache_data.clear()
            st.session_state.last_update = datetime.now()
            st.rerun()
    
    # 获取新闻数据
    with st.spinner("正在获取最新报道..."):
        articles = fetch_all_news(keywords, days_back)
    
    # 显示统计信息
    st.subheader(f"📊 共找到 {len(articles)} 篇相关报道")
    
    # 按来源分类统计
    if articles:
        df = pd.DataFrame(articles)
        
        # 统计图表
        col1, col2 = st.columns(2)
        with col1:
            source_counts = df['source'].value_counts()
            st.bar_chart(source_counts)
        
        with col2:
            # 时间分布
            df['date'] = pd.to_datetime(df['published']).dt.date
            date_counts = df['date'].value_counts().sort_index()
            st.line_chart(date_counts)
        
        # 显示新闻列表
        st.subheader("📰 最新报道")
        
        for idx, article in enumerate(articles):
            with st.expander(f"📌 {article['title']}"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**来源**: {article['source']} ({article['source_type']})")
                    st.markdown(f"**发布时间**: {article['published'].strftime('%Y-%m-%d %H:%M')}")
                    st.markdown(f"**匹配关键词**: `{article['matched_keywords']}`")
                    st.markdown(f"**摘要**: {article['snippet']}")
                    st.markdown(f"**原文链接**: [点击查看]({article['url']})")
                
                # 添加到监控列表的按钮
                if st.button("🔍 标记为重点关注", key=f"track_{idx}"):
                    if 'tracked' not in st.session_state:
                        st.session_state.tracked = []
                    if article['url'] not in st.session_state.tracked:
                        st.session_state.tracked.append(article['url'])
                        st.success("已添加到重点关注列表")
    else:
        st.warning("暂无相关报道，请稍后再试或调整关键词")
    
    # 侧边栏显示重点关注
    with st.sidebar:
        st.subheader("⭐ 重点关注")
        if 'tracked' in st.session_state and st.session_state.tracked:
            for url in st.session_state.tracked[-5:]:  # 显示最近5个
                st.markdown(f"- [{url}]({url})")
        else:
            st.info("暂无重点关注项目")
        
        st.markdown("---")
        st.caption("数据每6小时自动更新，手动刷新可获取最新数据")

if __name__ == "__main__":
    main()
