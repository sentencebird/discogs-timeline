import streamlit as st
from streamlit_timeline import timeline
import json

from bs4 import BeautifulSoup
import requests
import re
import dateutil
import urllib

def get_soup(url):
    response = requests.get(url)
    response.encoding = response.apparent_encoding
    html = response.text
    return BeautifulSoup(html, 'html.parser')


def search_pages(q, limit=12):
    url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={q}&limit={limit}&namespace=0&format=json"
    soup = get_soup(url)    
    return json.loads(soup.text)[3]

def search_title_by_page_url(page_url):
    title_uri = page_url.replace("https://en.wikipedia.org/wiki/", "")
    url = f"https://dbpedia.org/data/{title_uri}.json"
    soup = get_soup(url)
    dpedia_dict = json.loads(soup.text)
    title = urllib.parse.unquote(title_uri)
    if len(dpedia_dict) == 0: return title
    if "http://dbpedia.org/ontology/wikiPageRedirects" not in dpedia_dict[f"http://dbpedia.org/resource/{title}"]:
        return title
    dbpedia_url = dpedia_dict[f"http://dbpedia.org/resource/{title}"]["http://dbpedia.org/ontology/wikiPageRedirects"][0]["value"]
    return dbpedia_url.replace("http://dbpedia.org/resource/", "")

def fetch_img_url(title, size=150):
    url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&formatversion=2&prop=pageimages|pageterms&pithumbsize={size}&titles={title}"
    soup = get_soup(url)
    img_json = json.loads(soup.text)["query"]["pages"][0]
    img_url = img_json["thumbnail"]["source"] if "thumbnail" in img_json else "http://placehold.jp/150x150.png"
    return img_url

def fetch_section_index(title, section_title):
    url = f"https://en.wikipedia.org/w/api.php?action=parse&page={title}&prop=sections&format=json"
    soup = get_soup(url)
    sections = json.loads(soup.text)["parse"]["sections"]        
    for section in sections:
        if section["line"] == section_title: 
            return section["index"]
        
def fetch_text_by_index(title, index):
    url = f"https://en.wikipedia.org/w/api.php?action=parse&format=json&page={title}&prop=wikitext&section={index}"
    soup = get_soup(url)
    text = json.loads(soup.text)["parse"]["wikitext"]["*"]
    return text

def parse_discographies(text):
    matches = re.findall("\* ''\[\[.*?\]\]''", text)
    return [re.sub("\|.*$", "", m.replace("* ''[[", "").replace("]]''", "")).replace(" ", "_") for m in matches]

def fetch_album_info(title):
    url = f"https://en.wikipedia.org/w/api.php?action=parse&page={title}&prop=wikitext&section=0&format=json"
    soup = get_soup(url)
    text = json.loads(soup.text)["parse"]["wikitext"]["*"]
    if "{{Infobox album" not in text: return None
    
    name = _parse_info_by_arg("name", text)
    year = _parse_info_by_arg("year", text)
    cover_str = _parse_info_by_arg("cover", text)
    released_str = _parse_info_by_arg("released", text)
    released = _parse_date(released_str)

    if len(cover_str) > 0: 
        cover = fetch_img_url(f'File:{cover_str}')
    else:
        cover = ""
    
    return {"name": name,
            "released": released,
            "cover": cover,
            "url": f"https://en.wikipedia.org/wiki/{title}"
           }
    
def _parse_info_by_arg(arg, text):
    try:
        m = re.search(f"\| {arg}.*?$", text, flags=re.MULTILINE).group()
        return re.sub(f"\|[\s]*{arg}[\s]*= ", "", m).strip()
    except: return ""
    
def _parse_date(text):
    try:
        return dateutil.parser.parse(text)
    except: pass
    try: 
        return dateutil.parser.parse(re.sub(r"\D", "", text))
    except: pass
    try:
        year = re.search("[0-9]{4}", text).group()
        for month_name in [calendar.month_name, calendar.month_abbr]:
            if month in text:
                month = month_name
        return dateutil.parser.parse(f"{month} {year}")
    except: pass
    try: 
        year = re.search("[0-9]{4}", text).group()
        return dateutil.parser.parse(year)
    except: 
        return None
    
    

def artist_html(name, img_url):
    return \
    f"""
    <a href="?q={name}">
    <img src="{img_url}"></img> <div>{name.replace("_", " ")}</div>
    </a>
    """

def make_headline(name, img_url):
    name = name.replace("_", " ")
    return \
    {
        "title": {
            "media": {
              "url": img_url,
            },
            "text": {
              "headline": name,
              "text": f"<p>{name} - Discography</p>"
            }
        }
    }

def make_event(disc):
    return \
    {
        "media": {
          "url": disc["cover"]
        },
        "start_date": {
            "year": disc["released_year"],
            "month": disc["released_month"]
        },
        "text": {
            "headline": f'<a href="{disc["url"]}">{disc["name"]}</a>',
            "text": ""
        }
    }


st.set_page_config(page_title="Discography Timeline", layout="wide")
st.title("Discography Timeline")

params = st.experimental_get_query_params()

artist_name = ""

if "q" in params:
    artist_name = params["q"][0]

q = st.text_input("Artist", artist_name)

col1, col2, col3, col4 = st.columns(4)

if len(q) == 0: st.stop()
    
if q != artist_name:
    i = 0
    page_urls = search_pages(q)
    for page_url in page_urls:
        artist_name = search_title_by_page_url(page_url)
        artist_img_url = fetch_img_url(artist_name)
        if i > 12: break
        try:
            html = artist_html(artist_name, artist_img_url)
        except: continue

        exec(f'col = col{i % 4 + 1}')
        with col:
            st.markdown(html, unsafe_allow_html=True)
        i += 1
else:
    artist_img_url = fetch_img_url(artist_name)
    html = artist_html(artist_name, artist_img_url)    
    st.markdown(html, unsafe_allow_html=True)
    dic = make_headline(artist_name, artist_img_url)
    
    disc_index = fetch_section_index(artist_name, "Discography")
    text = fetch_text_by_index(artist_name, int(disc_index))
    disc_names = parse_discographies(text)
    discs = []
    for disc_name in disc_names:
        try:
            with st.spinner(f"Reading <{disc_name.replace('_', ' ')}>"):
                disc = fetch_album_info(disc_name)
                disc["released_year"] = disc["released"].year
                disc["released_month"] = disc["released"].month
            discs.append(make_event(disc))
        except: pass
    dic["events"] = discs
    timeline(json.dumps(dic))


