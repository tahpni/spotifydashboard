import os
import base64
import pandas as pd
from requests import post, get
from dotenv import load_dotenv
from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import json

load_dotenv()

# Spotify API credentials
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

def get_token():
    auth_string = f"{client_id}:{client_secret}"
    auth_base64 = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
    response = post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={"grant_type": "client_credentials"}
    )
    return response.json().get("access_token")

def get_auth_header(token):
    return {"Authorization": f"Bearer {token}"}

def search_artist(token, artist_name):
    response = get(
        f"https://api.spotify.com/v1/search?q={artist_name}&type=artist&limit=1",
        headers=get_auth_header(token)
    )
    items = response.json().get("artists", {}).get("items", [])
    return items[0] if items else -1

def get_top_tracks(token, artist_id):
    response = get(
        f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?country=US",
        headers=get_auth_header(token)
    )
    return response.json().get("tracks", []) or -1

def get_related_artists(token, artist_id):
    response = get(
        f"https://api.spotify.com/v1/artists/{artist_id}/related-artists",
        headers=get_auth_header(token)
    )
    if response.status_code == 200:
        return response.json().get("artists", [])
    return []

def load_data():
    return {
        "genres": [],
        "counts": [],
        "top_artists": ["Enter an artist's name to get started"],
        "genre_recommendations": ["Unfinished :)"]
    }

def create_pie_chart(genres):
    genre_counts = {genre: genres.count(genre) for genre in set(genres)}
    df = pd.DataFrame({"Genre": list(genre_counts.keys()), "Count": list(genre_counts.values())})
    fig = px.pie(
        df, names='Genre', values='Count', title='Genre Pie Chart',
        color_discrete_sequence=px.colors.sequential.RdBu
    )
    fig.update_traces(textinfo='percent+label')
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white'
    )
    return fig

def create_card(title, items, card_id):
    return dbc.Card(
        dbc.CardBody([
            html.H4(title, className='card-title text-light'),
            html.Ul(
                id=card_id,
                children=[html.Li(item, className='text-light') for item in items],
                style={'listStyleType': 'none', 'paddingLeft': 0}
            )
        ]),
        style={
            'marginBottom': '20px', 'boxShadow': '0 6px 12px rgba(0, 0, 0, 0.1)',
            'borderRadius': '8px', 'backgroundColor': '#343a40'
        }
    )

app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
data = load_data()

app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Fun Side Project", className='text-center my-4 text-light'))),
    dbc.Row([
        dbc.Col(dcc.Graph(id='pie-chart', figure=create_pie_chart(data["genres"])), md=6),
        dbc.Col([
            create_card("Top Songs", data["top_artists"], 'top-artists-list'),
            create_card("Related Artists", [], 'related-artists-list')
        ], md=6)
    ]),
    dbc.Row([
        dbc.Col(
            dbc.Input(
                id='artist-name-input',
                placeholder='Enter artist name...',
                type='text',
                className='mt-4 text-center',
                style={'borderRadius': '8px', 'backgroundColor': '#212529', 'color': 'white'}
            )
        ),
        dbc.Col(
            dbc.Button(
                "Search Artist", id='search-button', n_clicks=0, className='mt-4',
                style={'borderRadius': '8px', 'backgroundColor': '#28a745', 'color': 'white'}
            ),
            width='auto'
        )
    ], justify='center'),
], fluid=True)

@app.callback(
    [Output('top-artists-list', 'children'),
     Output('pie-chart', 'figure'),
     Output('related-artists-list', 'children')],
    Input('search-button', 'n_clicks'),
    State('artist-name-input', 'value')
)
def update_data(n_clicks, artist_name):
    if n_clicks > 0 and artist_name:
        token = get_token()
        artist_info = search_artist(token, artist_name)
        if artist_info == -1:
            return [html.Li(f"Artist '{artist_name}' not found")], create_pie_chart([]), []

        top_tracks = get_top_tracks(token, artist_info['id'])
        related_artists = get_related_artists(token, artist_info['id'])

        if top_tracks == -1:
            return [html.Li("No top tracks found", className='text-light')], create_pie_chart([]), []

        pie_chart = create_pie_chart(artist_info['genres'])
        related_artists_list = [html.Li(artist['name'], className='text-light') for artist in related_artists[:5]]

        return [html.Li(track['name'], className='text-light') for track in top_tracks], pie_chart, related_artists_list
    
    return [html.Li(artist, className='text-light') for artist in data["top_artists"]], create_pie_chart(data["genres"]), []

if __name__ == '__main__':
    app.run_server(debug=True)
