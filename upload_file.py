import base64
import datetime
import io
import dash
from dash import Dash, dcc, html, dash_table, Input, Output, State
import plotly.express as px
import pandas as pd


# Let's Define Python Jupyter methods first
def translate_tag(combined_df, tag_df):
    # deal with combined_df
    combined_df['Time'] = pd.to_datetime(combined_df[';Date'] + combined_df['Time'], format='%m/%d/%Y%H:%M:%S')
    df_pivot = combined_df.pivot_table(index='Time', columns='Tagname', values='Value')
    # deal with tag_df
    tag_df = tag_df.iloc[tag_df['变量名称'].dropna().index, :].reset_index()
    tagname = []
    # loop for each column name
    for j in range(len(df_pivot.columns)):
        flag = 0
        # loop for each tagname to real name
        for i in range(len(tag_df)):
            # change column names
            if tag_df['变量名称'][i] in list(df_pivot)[j]:
                flag = 1
                df_pivot.rename(columns={list(df_pivot)[j]: tag_df['说明'][i]}, inplace=True)
                break
        # drop this column
        if flag == 0:
            tagname.append(j)
    df_pivot.drop(df_pivot.columns[tagname], axis=1, inplace=True)
    df_pivot = pd.DataFrame(df_pivot)
    return df_pivot


# global
app = Dash(__name__)
dataframes = {}
dfs = []  # List to hold all dataframes
tag_df = None
dat = None
Timestamp = None

app.layout = html.Div([
    html.H1('Dashboard of Single Excel Sheet', style={'textAlign': 'center'}),
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        multiple=False
    ),
    html.Div(id='output-data-upload', children=[]),
    html.Button('Delete Last File', id='delete-button'),
    html.Button('Combine', id='combine-button', style={'margin-top': '10px'}),
    html.Div(id='output-combined-data', children=[]),  # Div to hold the combined data

    html.H2('Upload Independent Data', style={'textAlign': 'center'}),
    dcc.Upload(
        id='upload-data-ind',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        multiple=False
    ),
    html.Div(id='output-data-upload-ind', children=[]),  # Div to hold the independent data

    # Tag-Converter
    html.Button('Translate Data', id='translate-button', n_clicks=0),
    html.Div(id='output-translate-data', children=dash_table.DataTable(id='my-table', filter_action='native')),

    # Declare the DataTable with an initial empty state
    html.Button('Get Column Names', id='column-button', n_clicks=0),
    html.Div(id='dropdown-ind', children=dcc.Dropdown(id="dropdown", multi=True)),
    # Declare the Dropdown with an initial empty state
    html.Div(id="graph", children=dcc.Graph(id="scatter-matrix")),  # Declare the Graph with an initial empty state

    # Plotly
    html.Button('Get Column Names', id='column-button2', n_clicks=0),
    html.Div(id='dropdown-ind2', children=dcc.Dropdown(id="dropdown2", multi=True)),
    # Declare the Dropdown with an initial empty state
    html.Div(id="graph2", children=dcc.Graph(id="line-matrix")),  # Declare the Graph with an initial empty state
])


@app.callback(
    Output('output-data-upload', 'children'),
    [Input('upload-data', 'contents'),
     Input('upload-data', 'filename'),
     Input('upload-data', 'last_modified'),
     Input('delete-button', 'n_clicks')],
    State('output-data-upload', 'children'),
    prevent_initial_call=True
)
def update_output(contents, filename, date, delete_clicks, children):
    ctx = dash.callback_context
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'delete-button' and dataframes:
        deleted_df = dataframes.popitem()
        dfs.remove(deleted_df[1])
        children.pop()
        return children

    if contents is not None:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            if 'csv' in filename:
                # Assume that the user uploaded a CSV file
                df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), index_col=False)
            elif 'xls' in filename:
                # Assume that the user uploaded an Excel file
                df = pd.read_excel(io.BytesIO(decoded), index_col=False)

            dataframes[filename] = df  # Store the dataframe in the global variable
            dfs.append(df)  # Append dataframe to the list

            children.append(html.Div([
                html.H5(filename),
                html.Hr(),  # horizontal line
            ]))
        except Exception as e:
            print(e)
            return html.Div([
                'There was an error processing this file.'
            ])
    return children


@app.callback(
    Output('output-combined-data', 'children'),
    [Input('combine-button', 'n_clicks')],
    prevent_initial_call=True
)
def combine_data(n_clicks):
    if n_clicks and dfs:
        combined_df = pd.concat(dfs)
        # Create the table
        table = dash_table.DataTable(
            data=combined_df.head(10).to_dict('records'),  # Take 5 first and last rows
            columns=[{'name': i, 'id': i} for i in combined_df.columns],
            style_table={'overflowX': 'auto'},
            page_size=10,
        )
        return table
    else:
        return ""


@app.callback(
    Output('output-data-upload-ind', 'children'),
    [Input('upload-data-ind', 'contents'),
     Input('upload-data-ind', 'filename'),
     Input('upload-data-ind', 'last_modified')],
    prevent_initial_call=True
)
def update_output_ind(contents, filename, date):
    global tag_df
    if contents is not None:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            if 'csv' in filename:
                # Assume that the user uploaded a CSV file
                df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), index_col=False)
            elif 'xls' in filename:
                # Assume that the user uploaded an Excel file
                df = pd.read_excel(io.BytesIO(decoded), index_col=False)

            table = dash_table.DataTable(
                data=df.head(10).to_dict('records'),  # Take first 10 rows
                columns=[{'name': i, 'id': i} for i in df.columns],
                style_table={'overflowX': 'auto'}
            )
            tag_df = df
            return html.Div([
                html.H5(filename),
                html.Hr(),  # horizontal line
                table
            ])
        except Exception as e:
            print(e)
            return html.Div([
                'There was an error processing this file.'
            ])
    return []


@app.callback(
    Output('output-translate-data', 'children'),
    [Input('translate-button', 'n_clicks')],
    prevent_initial_call=True
)
def translate_data(n_clicks):
    global dat
    global Timestamp
    if n_clicks and dfs:
        df_pivot = translate_tag(pd.concat(dfs), tag_df)
        # Create the table
        table = dash_table.DataTable(
            id='my-table',  # Here we assign an ID to the table itself
            data=df_pivot.to_dict('records'),  # Take 5 first and last rows
            columns=[{'name': i, 'id': i} for i in df_pivot.columns],
            style_table={'overflowX': 'auto'},
            filter_action='native',
            page_size=10,
        )
        dat = df_pivot
        Timestamp = df_pivot.index
        return table
    else:
        return ""


@app.callback(
    Output('dropdown-ind', 'children'),
    [Input('column-button', 'n_clicks')],
    prevent_initial_call=True
)
def update_dropdown_ind(n_clicks):
    global dat
    if n_clicks is not None and dat is not None:
        dropdown = dcc.Dropdown(
            id="dropdown",
            options=[{'label': i, 'value': i} for i in dat.columns],
            multi=True
        )
        return dropdown
    else:
        return dash.no_update  # Return no update instead of empty string if conditions are not met


@app.callback(
    Output("graph", "children"),
    Input('my-table', 'derived_virtual_indices'),
    Input('dropdown', 'value'),
    State('my-table', 'data'),
    prevent_initial_call=True
)
def create_graphs(filtered_indices, selected_cols, all_data):
    if filtered_indices is None or selected_cols is None or all_data is None:
        return dash.no_update

    df = pd.DataFrame(all_data)
    dff = df[df.index.isin(filtered_indices)]

    fig = px.scatter_matrix(data_frame=dff[selected_cols])
    fig.update_traces(diagonal_visible=False)

    return dcc.Graph(id="scatter-matrix", figure=fig)


@app.callback(
    Output('dropdown-ind2', 'children'),
    [Input('column-button2', 'n_clicks')],
    prevent_initial_call=True
)
def update_dropdown_ind(n_clicks):
    global dat
    if n_clicks is not None and dat is not None:
        dropdown2 = dcc.Dropdown(
            id="dropdown2",
            options=[{'label': i, 'value': i} for i in dat.columns],
            multi=True
        )
        return dropdown2
    else:
        return dash.no_update  # Return no update instead of empty string if conditions are not met


@app.callback(
    Output("graph2", "children"),
    Input('my-table', 'derived_virtual_indices'),
    Input('dropdown2', 'value'),
    State('my-table', 'data'),
    prevent_initial_call=True
)
def create_graphs(filtered_indices, selected_cols, all_data):
    global Timestamp
    if filtered_indices is None or selected_cols is None or all_data is None:
        return dash.no_update
    df = pd.DataFrame(all_data)
    dff = df[df.index.isin(filtered_indices)]

    fig2 = px.line(data_frame=dff, x=Timestamp, y=selected_cols)
    return dcc.Graph(id="line-matrix", figure=fig2)


if __name__ == '__main__':
    app.run_server(debug=True)
