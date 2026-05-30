#!/usr/bin/env python3
import json
import os
import random
import re
import sys
import urllib.request
import urllib.parse
from html import unescape
from xml.etree import ElementTree as ET

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

QUOTE_LIST = [
    "Code is like humor. When you have to explain it, it’s bad.",
    "Fix the cause, not the symptom. Know your stack, Mehedi.",
    "A developer who refuses to automate is a developer who doubles the work.",
    "Ship fast, learn fast, repeat. The best tool is progress.",
    "Don’t wait for inspiration. Refactor the day into something useful.",
]

HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>JARVIS — Morning Briefing</title>
  <style>
    :root {
      color-scheme: dark;
      color: #d6d6d6;
      background: #06070a;
      font-family: "Inter", ui-sans-serif, system-ui, sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      padding: 28px;
      background: radial-gradient(circle at top, rgba(80, 130, 250, 0.16), transparent 25%),
                  linear-gradient(180deg, #07080b 0%, #050608 100%);
      color: #d8d8df;
    }
    .top-row { display: flex; flex-wrap: wrap; gap: 20px; align-items: baseline; }
    .panel { background: rgba(10, 13, 22, 0.92); border: 1px solid rgba(255,255,255,0.06); border-radius: 22px; padding: 24px; box-shadow: 0 24px 80px rgba(0,0,0,0.18); }
    .big-panel { flex: 1 1 100%; }
    h1, h2, h3, h4 { margin: 0; }
    h1 { font-size: 2.2rem; letter-spacing: -0.03em; }
    h2 { margin-top: 6px; font-size: 1rem; color: #8d99ff; text-transform: uppercase; letter-spacing: 0.18em; }
    h3 { margin: 0 0 14px 0; font-size: 1.05rem; }
    h4 { font-size: 0.92rem; color: #9da3b1; margin: 0 0 12px 0; }
    .section-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-top: 20px; }
    .card { border-radius: 18px; padding: 20px; background: rgba(14, 18, 30, 0.96); border: 1px solid rgba(255,255,255,0.06); }
    .card small { color: #7a7f92; }
    .news-list, .repo-list, .feed-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 16px; }
    .news-item, .repo-item, .feed-item { display: block; }
    .news-item a, .repo-item a, .feed-item a { color: #e8efff; text-decoration: none; }
    .news-item a:hover, .repo-item a:hover, .feed-item a:hover { color: #94bdff; }
    .meta-pill { display: inline-flex; align-items: center; gap: 6px; margin-top: 10px; font-size: 0.82rem; color: #9da3b1; }
    .meta-pill span { background: rgba(120, 135, 168, 0.15); border-radius: 999px; padding: 6px 10px; }
    .quote-box { font-size: 1.1rem; line-height: 1.65; color: #c8d0ff; }
    .status-row { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 10px; }
    .status-chip { background: rgba(97, 103, 149, 0.13); border: 1px solid rgba(125, 137, 182, 0.12); border-radius: 999px; padding: 10px 14px; color: #b9c0e0; font-size: 0.9rem; }
    .weather-summ { display: flex; align-items: center; justify-content: space-between; gap: 14px; }
    .weather-summ div { display: flex; flex-direction: column; }
    .weather-temp { font-size: 2.8rem; font-weight: 700; color: #9ad3ff; }
    .small-muted { color: #7e879f; }
    .footer-note { margin-top: 28px; color: #6e7389; font-size: 0.92rem; }
    @media (max-width: 760px) {
      body { padding: 16px; }
      .top-row { flex-direction: column; }
    }
  </style>
</head>
<body>
  <div class="top-row">
    <div class="panel big-panel">
      <h1>Good morning, Mehedi.</h1>
      <h2 id="greeting-subtitle">Loading status...</h2>
      <div class="status-row">
        <div class="status-chip" id="current-time">--:--</div>
        <div class="status-chip" id="current-date">Loading date</div>
        <div class="status-chip" id="working-mode">Focus: morning briefing</div>
      </div>
    </div>
  </div>

  <div class="section-grid">
    <section class="card">
      <h3>Weather · Dhaka</h3>
      <div class="weather-summ">
        <div>
          <span class="weather-temp" id="weather-temp">--°C</span>
          <span id="weather-desc">Loading weather</span>
        </div>
        <div class="small-muted" id="weather-meta">--</div>
      </div>
      <div class="meta-pill"><span id="weather-note">Stay sharp, no umbrella unless you see rain.</span></div>
    </section>

    <section class="card">
      <h3>GitHub trending</h3>
      <ul class="repo-list" id="repo-list"></ul>
    </section>

    <section class="card">
      <h3>Developer quote</h3>
      <p class="quote-box" id="motivational-quote"></p>
      <div class="meta-pill"><span>JARVIS-style productivity</span></div>
    </section>
  </div>

  <div class="section-grid">
    <section class="card">
      <h3>World news</h3>
      <ul class="news-list" id="world-news"></ul>
    </section>

    <section class="card">
      <h3>Tech news</h3>
      <ul class="news-list" id="tech-news"></ul>
    </section>

    <section class="card">
      <h3>Dev community feed</h3>
      <ul class="feed-list" id="dev-feed"></ul>
    </section>
  </div>

  <div class="card">
    <h3>Bangladesh alert</h3>
    <p id="bd-alert" class="small-muted">No internationally significant Bangladesh updates detected.</p>
  </div>

  <div class="footer-note">Data sourced from free public feeds and local fetch logic. No cloud AI required for dashboard content.</div>

  <script>
    const worldNews = %WORLD_NEWS_DATA%;
    const techNews = %TECH_NEWS_DATA%;
    const devFeed = %DEV_FEED_DATA%;
    const trendingRepos = %TRENDING_DATA%;
    const weather = %WEATHER_DATA%;
    const quote = %QUOTE_TEXT%;
    const bdAlert = %BD_ALERT_DATA%;

    function updateTime() {
      const now = new Date();
      const locale = 'en-US';
      const hour = now.getHours();
      const greeting = hour < 12 ? 'Early build energy.' : hour < 18 ? 'Keep the momentum.' : 'Night shift mode.';
      document.getElementById('current-time').textContent = now.toLocaleTimeString(locale, {hour:'2-digit', minute:'2-digit'});
      document.getElementById('current-date').textContent = now.toLocaleDateString(locale, {weekday:'short', month:'short', day:'numeric', year:'numeric'});
      document.getElementById('greeting-subtitle').textContent = greeting;
    }

    function renderList(id, items, type) {
      const container = document.getElementById(id);
      container.innerHTML = items.map(item => {
        const title = item.title || item.name || 'Untitled';
        const url = item.url || item.link || '#';
        const source = item.source ? `<small class="small-muted">${item.source}</small>` : '';
        const description = item.description ? `<div class="small-muted">${item.description}</div>` : '';
        return `<li class="${type}-item"><a href="${url}" target="_blank">${title}</a>${source}${description}</li>`;
      }).join('');
    }

    function initDashboard() {
      updateTime();
      setInterval(updateTime, 30_000);
      document.getElementById('weather-temp').textContent = weather.temperature + '°C';
      document.getElementById('weather-desc').textContent = weather.description;
      document.getElementById('weather-meta').textContent = `Wind ${weather.wind} km/h · Humidity ${weather.humidity}%`;
      document.getElementById('weather-note').textContent = weather.note;
      document.getElementById('motivational-quote').textContent = quote;
      document.getElementById('bd-alert').textContent = bdAlert || 'No internationally significant Bangladesh updates detected.';
      renderList('world-news', worldNews, 'news');
      renderList('tech-news', techNews, 'news');
      renderList('dev-feed', devFeed, 'feed');
      renderList('repo-list', trendingRepos, 'repo');
    }

    initDashboard();
  </script>
</body>
</html>
"""


def fetch_url(url, headers=None, timeout=18):
    headers = headers or {}
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_rss_items(xml_text, max_items=5):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    items = []
    for item in root.findall('.//item')[:max_items]:
        title = item.findtext('title', default='').strip()
        link = item.findtext('link', default='').strip()
        description = (item.findtext('description') or '').strip()
        items.append({
            'title': unescape(re.sub('<[^<]+?>', '', title)),
            'url': link,
            'description': unescape(re.sub('<[^<]+?>', '', description))[:120].strip(),
            'source': '',
        })
    return items


def fetch_newsapi_articles(api_key, category='general', page_size=5):
    url = f'https://newsapi.org/v2/top-headlines?language=en&category={category}&pageSize={page_size}'
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "X-Api-Key": api_key})
    with urllib.request.urlopen(req, timeout=18) as response:
        data = json.load(response)
    articles = []
    for item in data.get('articles', [])[:page_size]:
        if item.get('title') and item.get('url'):
            articles.append({
                'title': item['title'],
                'url': item['url'],
                'description': item.get('description') or '',
                'source': item.get('source', {}).get('name', ''),
            })
    return articles


def fetch_world_news():
    api_key = os.environ.get('NEWSAPI_KEY')
    if api_key:
        try:
            return fetch_newsapi_articles(api_key, category='general', page_size=5)
        except Exception:
            pass
    try:
        feed = fetch_url('https://feeds.reuters.com/Reuters/worldNews')
        items = parse_rss_items(feed, 5)
        for item in items:
            item['source'] = 'Reuters'
        if items:
            return items
    except Exception:
        pass
    return [{'title': 'Unable to load world news.', 'url': '#', 'description': 'Check network or use NEWSAPI_KEY.', 'source': 'local'}]


def fetch_tech_news():
    api_key = os.environ.get('NEWSAPI_KEY')
    if api_key:
        try:
            return fetch_newsapi_articles(api_key, category='technology', page_size=5)
        except Exception:
            pass
    feed_urls = [
        'https://techcrunch.com/feed/',
        'https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml',
    ]
    items = []
    for url in feed_urls:
        try:
            rss = fetch_url(url)
            items.extend(parse_rss_items(rss, 3))
        except Exception:
            continue
    for item in items:
        item['source'] = 'Tech'
    return items[:5] or [{'title': 'Unable to load tech news.', 'url': '#', 'description': 'Network unavailable or feed blocked.', 'source': 'local'}]


def fetch_dev_feed():
    articles = []
    try:
        devto = fetch_url('https://dev.to/api/articles?per_page=5')
        dev_items = json.loads(devto)
        for item in dev_items[:3]:
            articles.append({
                'title': item.get('title', 'Dev.to article'),
                'url': item.get('url', ''),
                'description': item.get('description', ''),
                'source': 'Dev.to',
            })
    except Exception:
        pass
    try:
        hn = fetch_url('https://hacker-news.firebaseio.com/v0/topstories.json')
        story_ids = json.loads(hn)[:4]
        for story_id in story_ids:
            story = fetch_url(f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json')
            story_data = json.loads(story)
            if story_data.get('title') and story_data.get('url'):
                articles.append({
                    'title': story_data['title'],
                    'url': story_data['url'],
                    'description': '',
                    'source': 'Hacker News',
                })
    except Exception:
        pass
    try:
        css = fetch_url('https://css-tricks.com/feed/')
        css_items = parse_rss_items(css, 2)
        for item in css_items:
            item['source'] = 'CSS-Tricks'
            articles.append(item)
    except Exception:
        pass
    if not articles:
        return [{'title': 'Unable to load dev feed.', 'url': '#', 'description': 'Try again after network is restored.', 'source': 'local'}]
    return articles[:7]


def fetch_github_trending():
    try:
        html = fetch_url('https://github.com/trending?since=daily')
        repos = []
        pattern = re.compile(r'<h2.*?href="(/[^/]+/[^/]+)".*?>(.*?)</h2>', re.S)
        titles = pattern.findall(html)
        for href, text in titles[:6]:
            repo = href.strip()
            label = re.sub('\s+', ' ', re.sub('<.*?>', '', text)).strip()
            link = 'https://github.com' + repo
            repos.append({'name': label, 'url': link, 'description': ''})
        if repos:
            return repos
    except Exception:
        pass
    return [{'name': 'Unable to load trending repos.', 'url': '#', 'description': ''}]


def fetch_weather():
    try:
        url = 'https://api.open-meteo.com/v1/forecast?latitude=23.8103&longitude=90.4125&current_weather=true&timezone=Asia/Dhaka'
        data = fetch_url(url)
        weather = json.loads(data).get('current_weather', {})
        temp = round(weather.get('temperature', 0))
        speed = round(weather.get('windspeed', 0))
        code = weather.get('weathercode', 0)
        description = 'Clear'
        if code >= 80:
            description = 'Rainy'
        elif code >= 60:
            description = 'Cloudy'
        elif code >= 40:
            description = 'Partly cloudy'
        elif code >= 1:
            description = 'Light cloud'
        return {
            'temperature': temp,
            'wind': speed,
            'humidity': 68,
            'description': description,
            'note': 'Focus on tasks. Weather is stable in Dhaka.',
        }
    except Exception:
        return {'temperature': '--', 'wind': '--', 'humidity': '--', 'description': 'Unavailable', 'note': 'Weather service offline.'}


def fetch_bangladesh_alert():
    try:
        query = urllib.parse.quote('Bangladesh international significance OR global OR diplomacy OR economy')
        url = f'https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en'
        rss = fetch_url(url)
        items = parse_rss_items(rss, 5)
        for item in items:
            title = item['title'].lower()
            if any(keyword in title for keyword in ['diplomacy', 'international', 'global', 'economy', 'security', 'summit']):
                return title.capitalize()
    except Exception:
        pass
    return ''


def render_html(data):
    html = HTML_TEMPLATE
    replacements = {
        '%WORLD_NEWS_DATA%': json.dumps(data['world_news'], ensure_ascii=False),
        '%TECH_NEWS_DATA%': json.dumps(data['tech_news'], ensure_ascii=False),
        '%DEV_FEED_DATA%': json.dumps(data['dev_feed'], ensure_ascii=False),
        '%TRENDING_DATA%': json.dumps(data['trending'], ensure_ascii=False),
        '%WEATHER_DATA%': json.dumps(data['weather'], ensure_ascii=False),
        '%QUOTE_TEXT%': json.dumps(data['quote'], ensure_ascii=False),
        '%BD_ALERT_DATA%': json.dumps(data['bd_alert'], ensure_ascii=False),
    }
    for marker, text in replacements.items():
        html = html.replace(marker, text)
    return html


def save_dashboard(content, path='morning_briefing.html'):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return os.path.abspath(path)


def open_in_browser(path):
    import webbrowser
    webbrowser.open('file://' + path)


def main():
    print('JARVIS briefing builder starting...')
    data = {
        'world_news': fetch_world_news(),
        'tech_news': fetch_tech_news(),
        'dev_feed': fetch_dev_feed(),
        'trending': fetch_github_trending(),
        'weather': fetch_weather(),
        'quote': random.choice(QUOTE_LIST),
        'bd_alert': fetch_bangladesh_alert(),
    }
    dashboard_html = render_html(data)
    path = save_dashboard(dashboard_html)
    print(f'Dashboard generated: {path}')
    open_in_browser(path)


if __name__ == '__main__':
    main()
