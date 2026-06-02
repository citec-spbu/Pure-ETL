import logging
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import dash
from dash import html, dcc, Input, Output
import dash_cytoscape as cyto
import dash_bootstrap_components as dbc
from collections import Counter
import networkx as nx
import requests
from datetime import datetime


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== CONFIGURATION =====
MAIN_AUTHORS = [
    'Oleg I. Drivotin',
    'Ivan S. Blekanov',
    'Aleksandra B. Vakaeva',
    'Sergey A. Kostyrko',
    'Mikhail A. Grekov',
    'E. A. Lejnina',
    'Alexander Krylatov',
    'Natalia Kizhaeva',
]

BASE_URL = "https://api.openalex.org"


COLOR_PALETTE = [
    '#FF3333', '#33CC33', '#3399FF', '#FF9933', '#9933CC',
    '#FF33CC', '#33CCCC', '#CC3333', '#33CC99', '#CC9933',
    '#993366', '#339966', '#CC3366', '#33CC66', '#FF6633',
    '#6633CC', '#FF33FF', '#33FF33', '#FFCC33', '#33FFCC'
]


# ===== DATA FETCHING FUNCTIONS =====
def get_author_id(display_name):
    url = f"{BASE_URL}/authors"
    params = {'search': display_name, 'select': 'id,display_name'}
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data['meta']['count'] > 0:
                author = data['results'][0]
                logger.info(f"Found author: {author['display_name']}")
                return author['id']
        logger.warning(f"Author {display_name} not found")
    except Exception as e:
        logger.error(f"Error searching for {display_name}: {e}")
    return None


def get_author_works(author_id):
    works = []
    url = f"{BASE_URL}/works"
    params = {'filter': f'author.id:{author_id}', 'per-page': 200}

    while url:
        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()
            works.extend(data['results'])
            url = data.get('next')
            params = None
        except Exception as e:
            logger.error(f"Error fetching works: {e}")
            break
    return works


def fetch_all_data():
    all_works = {}

    for author_name in MAIN_AUTHORS:
        author_id = get_author_id(author_name)
        if not author_id:
            continue

        works_list = get_author_works(author_id)
        for work in works_list:
            wid = work['id']
            if wid not in all_works:
                all_works[wid] = work

        logger.info(f"{author_name}: loaded {len(works_list)} works")

    return all_works


def extract_paper_info(work):
    primary_loc = work.get('primary_location') or {}
    source = (primary_loc.get('source') or {}).get('display_name', '')

    authors = []
    for a in work.get('authorships', []):
        if a.get('author'):
            authors.append(a['author'].get('display_name', ''))

    topics = []
    if work.get('primary_topic'):
        topics.append(work['primary_topic'].get('display_name', ''))

    return {
        'id': work['id'],
        'title': work.get('title', 'Untitled'),
        'authors': '; '.join(authors),
        'cited_by_count': work.get('cited_by_count', 0),
        'publication_year': work.get('publication_year', ''),
        'journal': source,
        'topics': topics,
    }


def build_coauthorship_graph(works_data):
    G = nx.Graph()

    for work_id, work in works_data.items():
        paper_info = extract_paper_info(work)
        authors = [a.strip() for a in paper_info['authors'].split(';') if a.strip()]

        for author in authors:
            if author not in G:
                G.add_node(author,
                           publications=0,
                           total_citations=0,
                           is_main_author=author in MAIN_AUTHORS)
            G.nodes[author]['publications'] += 1
            G.nodes[author]['total_citations'] += paper_info['cited_by_count']

        for i, a1 in enumerate(authors):
            for a2 in authors[i + 1:]:
                if G.has_edge(a1, a2):
                    G[a1][a2]['weight'] += 1
                else:
                    G.add_edge(a1, a2, weight=1)

    return G


def graph_to_cytoscape_elements(G):
    nodes = []
    edges = []

    # Assign colors to non-main authors
    color_idx = 0
    node_colors = {}

    for node in G.nodes():
        is_main = G.nodes[node].get('is_main_author', False)

        if is_main:
            node_color = '#E74C3C'
        else:
            if node not in node_colors:
                node_colors[node] = COLOR_PALETTE[color_idx % len(COLOR_PALETTE)]
                color_idx += 1
            node_color = node_colors[node]

        pubs = G.nodes[node].get('publications', 1)
        node_size = 20 + min(pubs, 30)

        nodes.append({
            'data': {
                'id': node,
                'label': node.split()[-1] if len(node.split()) > 1 else node,
                'full_name': node,
                'publications': pubs,
                'citations': G.nodes[node].get('total_citations', 0),
                'is_main_author': is_main,
                'node_size': node_size,
                'color': node_color
            }
        })


    for u, v, data in G.edges(data=True):
        edges.append({
            'data': {
                'source': u,
                'target': v,
                'weight': data.get('weight', 1)
            }
        })

    return nodes, edges



app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server

# ===== LOAD DATA =====
logger.info("Fetching data from OpenAlex...")
works_data = fetch_all_data()
logger.info(f"Loaded {len(works_data)} unique publications")

# Build graph
G = build_coauthorship_graph(works_data)
nodes, edges = graph_to_cytoscape_elements(G)

# Prepare data for analysis
df_papers = pd.DataFrame([extract_paper_info(w) for w in works_data.values()])

# Topic analysis
all_topics = []
for topics in df_papers['topics'].dropna():
    all_topics.extend(topics)
topic_counts = Counter(all_topics)
top_topics = topic_counts.most_common(10)

# Yearly publication trends
yearly_data = df_papers['publication_year'].value_counts().sort_index()

# Get max citations for slider
max_citations = int(df_papers['cited_by_count'].max()) if len(df_papers) > 0 else 100

logger.info(f"Graph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")

# ===== STYLESHEET =====
stylesheet = [
    {
        'selector': 'node',
        'style': {
            'width': 'data(node_size)',
            'height': 'data(node_size)',
            'background-color': 'data(color)',
            'label': 'data(label)',
            'font-size': '10px',
            'font-weight': 'bold',
            'text-valign': 'center',
            'text-halign': 'center',
            'color': '#FFFFFF',
            'text-outline-width': 1,
            'text-outline-color': '#333333',
            'border-width': 2,
            'border-color': '#FFFFFF'
        }
    },
    {
        'selector': 'edge',
        'style': {
            'width': 1.0,  # Более тонкие ребра (было 1.5)
            'line-color': '##9a9b9c',
            'curve-style': 'bezier',
            'opacity': 0.6
        }
    }
]

# ===== DASHBOARD LAYOUT =====
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("📊 SPBU Research Collaboration Network",
                    className="text-center mt-4 mb-2",
                    style={'color': '#2c3e50', 'font-weight': 'bold'}),
            html.P("Analysis of co-authorship patterns and research topics",
                   className="text-center text-muted mb-4"),
            html.Hr()
        ], width=12)
    ]),

    dbc.Row([
        # LEFT COLUMN - Graph
        dbc.Col([
            html.Div([
                html.H5("🔬 Co-authorship Network", className="mb-3"),
                cyto.Cytoscape(
                    id='coauthorship-graph',
                    elements=nodes + edges,
                    stylesheet=stylesheet,
                    layout={
                        'name': 'cose',
                        'idealEdgeLength': 120,
                        'nodeOverlap': 25,
                        'fit': True,
                        'padding': 40,
                        'nodeRepulsion': 400000,
                        'gravity': 80
                    },
                    style={'width': '100%', 'height': '600px', 'border': '1px solid #e0e0e0', 'borderRadius': '8px'},
                    minZoom=0.2,
                    maxZoom=2,
                    zoomingEnabled=True,
                    userZoomingEnabled=True,
                    panningEnabled=True,
                    userPanningEnabled=True
                ),
                html.Div([
                    html.Small(" 💡 Click nodes for details | Drag to rearrange", className="text-muted")
                ], className="text-center mt-3")
            ])
        ], width=8),

        # RIGHT COLUMN - Sidebar
        dbc.Col([
            # Filters
            html.Div([
                html.H6("🎛️ Filters", className="mb-3"),
                html.Label("Min Publications:", className="small"),
                dcc.Slider(
                    id='min-pubs-slider',
                    min=1,
                    max=20,
                    step=1,
                    value=1,
                    marks={i: str(i) for i in [1, 5, 10, 15, 20]}
                ),
                html.Label("Min Citations:", className="small mt-3"),
                dcc.Slider(
                    id='min-cites-slider',
                    min=0,
                    max=max_citations,
                    step=1,
                    value=0,
                    marks={0: '0', max_citations // 2: str(max_citations // 2), max_citations: str(max_citations)}
                ),
                dbc.Checkbox(
                    id='show-labels',
                    label="Show full names",
                    value=False,
                    className="mt-3"
                ),
                html.Hr(),
                html.Div([
                    html.Span("🔴 ", style={'color': '#E74C3C'}),
                    html.Small("Main SPbSU authors"),
                    html.Br(),
                    html.Span("🟢 ", style={'color': '#4ECDC4'}),
                    html.Small("Collaborators")
                ], className="small")
            ], className="p-3 mb-3",
                style={'backgroundColor': 'white', 'borderRadius': '8px', 'border': '1px solid #e0e0e0'}),

            # Node Info
            html.Div([
                html.H6("📌 Author Info", className="mb-3"),
                html.Div(id="node-info", children=[
                    html.Div("Click on any node", className="text-center text-muted py-4")
                ], style={'maxHeight': '350px', 'overflowY': 'auto'})
            ], className="p-3 mb-3",
                style={'backgroundColor': 'white', 'borderRadius': '8px', 'border': '1px solid #e0e0e0'}),

            # Statistics
            html.Div([
                html.H6("📊 Statistics", className="mb-3"),
                dbc.Row([
                    dbc.Col(html.Div([
                        html.Div("📚", style={'font-size': '20px'}),
                        html.Div(f"{len(df_papers)}", style={'font-size': '24px', 'font-weight': 'bold'}),
                        html.Div("Papers", className="small text-muted")
                    ], className="text-center p-2"), width=6),
                    dbc.Col(html.Div([
                        html.Div("👥", style={'font-size': '20px'}),
                        html.Div(f"{G.number_of_nodes()}", style={'font-size': '24px', 'font-weight': 'bold'}),
                        html.Div("Authors", className="small text-muted")
                    ], className="text-center p-2"), width=6),
                ]),
                dbc.Row([
                    dbc.Col(html.Div([
                        html.Div("🔗", style={'font-size': '20px'}),
                        html.Div(f"{G.number_of_edges()}", style={'font-size': '24px', 'font-weight': 'bold'}),
                        html.Div("Connections", className="small text-muted")
                    ], className="text-center p-2"), width=6),
                    dbc.Col(html.Div([
                        html.Div("📖", style={'font-size': '20px'}),
                        html.Div(f"{df_papers['cited_by_count'].sum():,}",
                                 style={'font-size': '20px', 'font-weight': 'bold'}),
                        html.Div("Citations", className="small text-muted")
                    ], className="text-center p-2"), width=6),
                ]),
            ], className="p-3",
                style={'backgroundColor': 'white', 'borderRadius': '8px', 'border': '1px solid #e0e0e0'})
        ], width=4)
    ], className="mb-4"),

    # Bottom charts
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H6("🏷️ Top Research Topics", className="mb-3"),
                dcc.Graph(id='topics-chart', config={'displayModeBar': False})
            ], className="p-3",
                style={'backgroundColor': 'white', 'borderRadius': '8px', 'border': '1px solid #e0e0e0'})
        ], width=6),
        dbc.Col([
            html.Div([
                html.H6("📈 Publication Trends", className="mb-3"),
                dcc.Graph(id='yearly-trend', config={'displayModeBar': False})
            ], className="p-3",
                style={'backgroundColor': 'white', 'borderRadius': '8px', 'border': '1px solid #e0e0e0'})
        ], width=6),
    ])
], fluid=True, className="p-4", style={'backgroundColor': '#f5f5f5'})


# ===== CALLBACKS =====

@app.callback(
    Output("node-info", "children"),
    [Input("coauthorship-graph", "selectedNodeData")]
)
def display_node_info(selected_nodes):
    if not selected_nodes:
        return html.Div("Click on any node", className="text-center text-muted py-4")

    node = selected_nodes[0]
    full_name = node.get('full_name', node.get('label', 'Unknown'))
    pubs = node.get('publications', 0)
    cites = node.get('citations', 0)
    is_main = node.get('is_main_author', False)

    # Find ALL collaborators
    collaborators = []
    for edge in edges:
        if edge['data']['source'] == full_name:
            collaborators.append(edge['data']['target'])
        elif edge['data']['target'] == full_name:
            collaborators.append(edge['data']['source'])

    # Sort collaborators by name for better readability
    collaborators.sort()

    # Display all collaborators
    collaborators_html = []
    if collaborators:
        for collab in collaborators:
            # Check if this collaborator is a main author
            is_collab_main = any(main_author.lower() in collab.lower() for main_author in MAIN_AUTHORS)
            collab_style = {'color': '#E74C3C'} if is_collab_main else {'color': '#2c3e50'}
            collaborators_html.append(html.Div(f"• {collab}", style=collab_style, className="small mb-1"))
    else:
        collaborators_html.append(html.Div("None", className="small text-muted"))

    return html.Div([
        html.H6(full_name, style={'color': '#E74C3C' if is_main else '#3498db'}),
        html.Hr(),
        html.Div([
            html.Div(f"📄 Publications: {pubs}"),
            html.Div(f"📊 Citations: {cites:,}"),
            html.Div(f"👥 Collaborators: {len(collaborators)}"),
            html.Div(f"⭐ Main author: {'Yes' if is_main else 'No'}")
        ], className="small"),
        html.Hr(),
        html.Div("🤝 Collaborators:", className="small fw-bold mb-2"),
        html.Div(collaborators_html, className="small")
    ])


@app.callback(
    [Output("coauthorship-graph", "elements"),
     Output("coauthorship-graph", "stylesheet")],
    [Input("min-pubs-slider", "value"),
     Input("min-cites-slider", "value"),
     Input("show-labels", "value")]
)
def update_graph(min_pubs, min_cites, show_labels):
    # Filter nodes
    filtered_nodes = []
    for node in nodes:
        if node['data']['publications'] >= min_pubs and node['data']['citations'] >= min_cites:
            filtered_nodes.append(node)

    # Filter edges
    filtered_node_ids = {node['data']['id'] for node in filtered_nodes}
    filtered_edges = [
        edge for edge in edges
        if edge['data']['source'] in filtered_node_ids and edge['data']['target'] in filtered_node_ids
    ]

    # Update stylesheet for labels
    updated_stylesheet = stylesheet.copy()
    if show_labels:
        for style in updated_stylesheet:
            if style.get('selector') == 'node':
                style['style']['label'] = 'data(full_name)'
                style['style']['font-size'] = '8px'
    else:
        for style in updated_stylesheet:
            if style.get('selector') == 'node':
                style['style']['label'] = 'data(label)'

    return filtered_nodes + filtered_edges, updated_stylesheet


@app.callback(
    Output("yearly-trend", "figure"),
    [Input("min-pubs-slider", "value"),
     Input("min-cites-slider", "value")]
)
def update_yearly_trend(min_pubs, min_cites):
    # Filter authors based on criteria
    filtered_author_names = []
    for node in nodes:
        if node['data']['publications'] >= min_pubs and node['data']['citations'] >= min_cites:
            filtered_author_names.append(node['data']['full_name'])

    # Filter papers
    if filtered_author_names:
        mask = df_papers['authors'].apply(
            lambda x: any(author in str(x) for author in filtered_author_names)
        )
        filtered_df = df_papers[mask]
    else:
        filtered_df = df_papers

    yearly_data_filtered = filtered_df['publication_year'].value_counts().sort_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=yearly_data_filtered.index,
        y=yearly_data_filtered.values,
        marker_color='#3498db',
        text=yearly_data_filtered.values,
        textposition='auto'
    ))
    fig.update_layout(
        title=None,
        xaxis_title="Year",
        yaxis_title="Papers",
        height=300,
        margin=dict(l=40, r=20, t=20, b=40),
        plot_bgcolor='white'
    )
    fig.update_xaxes(showgrid=True, gridcolor='#e0e0e0')
    fig.update_yaxes(showgrid=True, gridcolor='#e0e0e0')

    return fig


@app.callback(
    Output("topics-chart", "figure"),
    [Input("min-pubs-slider", "value"),
     Input("min-cites-slider", "value")]
)
def update_topics_chart(min_pubs, min_cites):
    # Filter authors based on criteria
    filtered_author_names = []
    for node in nodes:
        if node['data']['publications'] >= min_pubs and node['data']['citations'] >= min_cites:
            filtered_author_names.append(node['data']['full_name'])

    # Filter papers
    if filtered_author_names:
        mask = df_papers['authors'].apply(
            lambda x: any(author in str(x) for author in filtered_author_names)
        )
        filtered_df = df_papers[mask]
    else:
        filtered_df = df_papers

    # Count topics
    topics = []
    for topics_list in filtered_df['topics'].dropna():
        topics.extend(topics_list)
    topic_counts_filtered = Counter(topics)
    top_topics_filtered = topic_counts_filtered.most_common(10)

    if not top_topics_filtered:
        fig = go.Figure()
        fig.update_layout(title="No data for selected filters", height=300)
        return fig

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[count for topic, count in top_topics_filtered[::-1]],
        y=[topic[:50] + '...' if len(topic) > 50 else topic for topic, count in top_topics_filtered[::-1]],
        orientation='h',
        marker_color='#E74C3C',
        text=[count for topic, count in top_topics_filtered[::-1]],
        textposition='outside'
    ))
    fig.update_layout(
        title=None,
        xaxis_title="Publications",
        yaxis_title="",
        height=300,
        margin=dict(l=160, r=20, t=20, b=20),
        plot_bgcolor='white'
    )
    fig.update_xaxes(showgrid=True, gridcolor='#e0e0e0')

    return fig


if __name__ == '__main__':
    app.run(debug=True, port=8050)