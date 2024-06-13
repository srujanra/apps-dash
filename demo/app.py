import sys
from os.path import dirname
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html
from src.about import tt_description
from src.timetables import CONTRACT_TYPES

sys.path.append(dirname(__file__))

app = dash.Dash(
    __name__, use_pages=True, external_stylesheets=[dbc.themes.SOLAR]
)
server = app.server

SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "24%",
    "padding": "1rem 1rem",
}

# Nav to select the page
report_nav = dbc.Nav(
    [
        dbc.NavLink(
            html.Div(page["name"], className="ms-2"),
            href=page["path"],
            active="exact",
        )
        for page in dash.page_registry.values()
    ],
    vertical=False,
    pills=True,
)

# Contract editor
contract_editor = html.Div(
    [
        dcc.Dropdown(
            ["SPX", "EUR", "BTC", "FTSE"],
            "SPX",
            id="ctr-ticker",
        ),
        html.Br(),
        dcc.Dropdown(
            CONTRACT_TYPES,
            CONTRACT_TYPES[0],
            id="ctr-type",
        ),
        html.Br(),
        html.Div(
            [
                html.Label("Option Type", style={'margin-right': '10px', 'min-width': '100px'}),  # Header for Option Type
                dcc.RadioItems(
                    options=[
                        {'label': 'Call', 'value': 'Call'},
                        {'label': 'Put', 'value': 'Put'}
                    ],
                    value='Call',
                    id='ctr-option-type',
                    inline=True,
                    labelStyle={'margin-right': '20px', 'display': 'inline-block'}  # Add spacing between radio buttons
                ),
            ],
            style={'display': 'flex', 'align-items': 'center'}
        ),
        html.Br(),
        html.Div(
            [
                html.Label("Strike", style={'margin-right': '10px', 'min-width': '50px'}),
                html.Div(
                    dcc.Slider(
                        id='ctr-strike',
                        min=80,
                        max=120,
                        step=1,
                        value=100,
                        marks={i: f'{i}%' for i in range(80, 121, 10)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    style={'flex': '1'}
                ),
            ],
            style={'display': 'flex', 'align-items': 'center', 'width': '100%'}
        ),
        html.Br(),
        html.Div(
            [
                html.Label("Floor", style={'margin-right': '10px', 'min-width': '60px'}),
                html.Div(
                    dcc.RangeSlider(
                        id='ctr-cap-floor',
                        min=-10,
                        max=10,
                        step=0.1,
                        value=[-5, 5],
                        marks={i: f'{i}%' for i in range(-10, 11, 5)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    style={'flex': '1'}
                ),
                html.Label("Cap", style={'margin-left': '10px', 'min-width': '60px'})
            ],
            style={'display': 'flex', 'align-items': 'center', 'width': '100%'}
        ),
        dcc.Store(id="ctr-params", storage_type="session"),
        html.Br(),
        dbc.Button(
            "About this Contract",
            id="open-offcanvas",
            n_clicks=0,
            style={"backgroundColor": "#C08261"},
        ),
    ],
    id="contractr-params",
)

# Sidebar has the Pages Nav (Top), and Contract Editor (Below).
sidebar = html.Div(
    [
        html.Img(src="assets/logo.png", width="50%"),
        html.P(
            "Explore a variety of financial contracts through two lenses.",
            className="lead",
        ),
        report_nav,
        html.Br(),
        html.H2("Contract"),
        html.Hr(),
        contract_editor,
    ],
    style=SIDEBAR_STYLE,
)

# The app has sidebar on left, the pages are on the right.
# The pages area is populated by one of the scripts in the /pages folder.
app.layout = dbc.Container(
    [
        sidebar,
        dash.page_container,
        dbc.Offcanvas(
            [
                dcc.Markdown(id="offcanvas-body"),
                html.A(
                    href="https://www.qablet.com",
                    children=["qablet.com"],
                ),
            ],
            id="offcanvas",
            title="About this Contract",
            is_open=False,
            placement="end",
        ),
    ],
)


# Collect parameters from the contract editor and store them in a dict.
@callback(
    Output("ctr-params", "data"),
    Input("ctr-ticker", "value"),
    Input("ctr-type", "value"),
    Input("ctr-option-type", "value"),
    Input("ctr-strike", "value"),
    Input("ctr-cap-floor", "value"),
)
def update_graph(ticker, contract_type, option_type, strike, cap_floor):
    contract_params = {
        "ticker": ticker,
        "ctr-type": contract_type,
        "option_type": option_type,
        "strike": strike,
        "cap_floor": cap_floor[::-1],  # Reverse the order to get [cap, floor]
    }
    return contract_params


# Toggle the offcanvas to show the contract description.
@callback(
    Output("offcanvas", "is_open"),
    Output("offcanvas-body", "children"),
    [Input("open-offcanvas", "n_clicks")],
    [State("offcanvas", "is_open"), State("ctr-params", "data")],
)
def toggle_offcanvas(n1, is_open, contract_params):
    if n1:
        is_open = not is_open

    if is_open:
        text = tt_description(contract_params)
    else:
        text = ""

    return is_open, text


if __name__ == "__main__":
    app.run_server(debug=True)
