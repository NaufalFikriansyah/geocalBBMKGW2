import os
import json
from unicodedata import name
import plotly
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from obspy import read
from array import *
from datetime import timedelta
from scipy.signal import find_peaks
from werkzeug.utils import secure_filename
from flask import Flask, flash, render_template, request, redirect, send_file, url_for
from waitress import serve

app = Flask(__name__, static_url_path="", static_folder='static')
UPLOAD_FOLDER = "static/uploads/"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        
        if file.filename == '':
            flash('No selected file')

        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            return redirect(url_for('split', name=filename))

    return render_template('index.html')

@app.route('/split/<name>')
def split(name):
    st = read(os.path.join(UPLOAD_FOLDER, name))
    tr = st[0]

    time = []
    data = []

    ''' 
    0.05 second per data
    untuk data per menit dibutuhkan 0.05 * x = 60 detik
    x = 60 / 0.05
    = 1200 data
    '''

    start = tr.times("utcdatetime")[0]
    timeone = tr.times("utcdatetime")[1]

    delay = timeone-start

    istart = 0
    iend = len(tr.data)

    for i in range(int(istart), int(iend)):
        time.append(start + timedelta(seconds = i*delay))

    for i in range(int(istart), int(iend)):
        data.append(tr.data[i])

    alldata = {
        "times": time,
        "datas": data
    }

    df = pd.DataFrame(alldata)
    
    fig = px.line(df, x='times', y='datas')
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('split.html', graphJSON=graphJSON, text=name)

@app.route('/calibrate')
def calibrate():
    name = request.args.get('filename')

    st = read(os.path.join(UPLOAD_FOLDER, name))
    tr = st[0]

    filename =  request.args.get('filename')
    jamsatus =  request.args.get('jamsatus', type=float)
    menitsatus =  request.args.get('menitsatus', type=float)
    jamsatue =  request.args.get('jamsatue', type=float)
    menitsatue =  request.args.get('menitsatue', type=float)
    tegangan =  request.args.get('tegangan', type=float)
    frekuensi =  request.args.get('frekuensi', type=float)

    time = []
    data = []

    start = tr.times("utcdatetime")[0]
    timeone = tr.times("utcdatetime")[1]

    delay = timeone-start

    istart = ((3600/delay)*jamsatus)+((60/delay)*menitsatus) 
    iend = ((3600/delay)*jamsatue)+((60/delay)*menitsatue)

    for i in range(int(istart), int(iend)):
        time.append(i-istart)

    for i in range(int(istart), int(iend)):
        data.append(tr.data[i])

    alldata = {
        "times": time,
        "datas": data
    }

    df = pd.DataFrame(alldata)

    upper_treshold = 340000
    bottom_treshold = 220000
    peak, datapeak = find_peaks(data, height=upper_treshold)

    
    invdata = []
    vdata = []
    pdata = []

    for i in range(0, len(data)):
        invdata.append(-data[i])
    
    valley, datavalley = find_peaks(invdata, height=bottom_treshold)

    for i in range(0, len(datavalley['peak_heights'])):
        vdata.append(-datavalley['peak_heights'][i])
    for i in range(0, len(datapeak['peak_heights'])):
        pdata.append(datapeak['peak_heights'][i])

    fig = px.line(df, x='times', y='datas')
    fig.add_trace(go.Scatter(mode="markers", x=peak, y=datapeak['peak_heights'], name="puncak"))
    fig.add_trace(go.Scatter(mode="markers", x=valley, y=vdata, name="lembah"))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    '''
    peak = {
        "peak": datapeak['peak_heights'],
        "y": peak
    }

    dfpeak = pd.DataFrame(peak)
    dfpeak.to_csv('peak.csv')

    valley = {
        "valley": -datavalley['peak_heights'],
        "y": valley
    }

    dfvalley = pd.DataFrame(valley)
    dfvalley.to_csv('valley.csv')
    '''
    
    return render_template('calibrated.html', graphJSON=graphJSON, filename=filename, pdata=pdata, vdata=vdata, tegangan=tegangan, frekuensi=frekuensi)

if __name__ == '__main__':
    app.run(debug=True)
    #serve(app, host="0.0.0.0", port=5000)