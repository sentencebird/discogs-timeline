import streamlit as st
from streamlit_timeline import timeline
import discogs_client
import json

def artist_html(artist):
    img_url = artist.images[0]["uri150"] if artist.images is not None else "http://placehold.jp/150x150.png"
    return \
    f"""
    <a href="?q={artist.id}">
    <img src="{img_url}"></img> <div>{artist.name}</div>
    </a>
    """

def make_headline(artist):
    return \
    {
        "title": {
            "media": {
              "url": artist.images[0]["uri"],
            },
            "text": {
              "headline": artist.name,
              "text": f"<p>{artist.name} - Discography</p>"
            }
        }
    }

def make_event(release, artist):
    if release.data["type"] != "master" or \
    "year" not in release.data or \
    artist not in release.main_release.artists:
        return None
    
    return \
    {
        "media": {
          "url": release.data["thumb"]
        },
        "start_date": {
            "year": release.data["year"]
        },
        "text": {
            "headline": release.title,
            "text": f'<a href="{release.url}"></a>'
        }
    }
        

d = discogs_client.Client('ExampleApplication/0.1', user_token="tRczqPfXDvqBWWTARrUMOZNQyJFtfuWhiXcMKfFx")

st.set_page_config(page_title="Discography Timeline", layout="wide")

params = st.experimental_get_query_params()

artist_name = ""

if "q" in params:
    artist = d.artist(params["q"][0])
    artist_name = artist.name

q = st.text_input("Artist", artist_name)

col1, col2, col3, col4 = st.columns(4)

if len(q) == 0: st.stop()
    
if q != artist_name:
    i = 0
    artists = d.search(q, type='artist')
    for artist in artists:
        if i > 12: break
        try:
            html = artist_html(artist)
        except: continue

        exec(f'col = col{i % 4 + 1}')
        with col:
            st.markdown(html, unsafe_allow_html=True)
        i += 1
else:
    html = artist_html(artist)    
    st.markdown(html, unsafe_allow_html=True)
    
    years = st.slider('Years', 1950, 2020, (1965, 1980))
    dic = make_headline(artist)
    
    if st.button("Search Releases"):
        events = []
        for year in range(years[0], years[1], 1):
            with st.spinner(f"Search releases in {year}..."):
                releases = d.search(artist=artist.name, type="master", format="album", year=year)
                for release in releases:
                    event = make_event(release, artist)
                    if event is None: continue
                    events.append(event)
                    dic["events"] = events
        timeline(json.dumps(dic), height=800)


