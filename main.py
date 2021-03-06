import pandas as pd
import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import os
from copy import copy


def get_n_participants(fname, label = ''):
    # csvの読み込み
    df = pd.read_csv(fname)

    # 時刻の部分だけ抜き取り
    df_start_end = df.loc[:, ['参加時刻', '退出時刻']]

    # Zoomの時刻表示をdatetimeオブジェクトに変換する関数を定義(pandas.dataframeに一括適用できるように定義)
    datetime_format = '%Y/%m/%d %I:%M:%S %p'
    str2datetime = lambda x:np.frompyfunc(lambda x:datetime.datetime.strptime(x, datetime_format), 1, 1)(x).astype(np.datetime64)

    # str → datetime.datetime
    df_start_end = str2datetime(df_start_end)

    sr_start = (df_start_end.iloc[:, 0]).dt.floor('min')  # 秒以下を切り捨てした入室時間
    sr_end = (df_start_end.iloc[:, 1]).dt.ceil('min') # 秒以下を切り上げした退出時間

    starttime = sr_start.min()  # 一番最初に参加した人の時刻
    endtime = sr_end.max()      # 一番最後に退出した人の時刻
    lst_n_participants = [0] * ((endtime - starttime).seconds // 60 + 1)    # 人数の入室・退室を管理するためのリスト

    # 入室，退出を検知して保存
    for s, e in zip(sr_start, sr_end):
        lst_n_participants[(s - starttime).seconds // 60] += 1
        lst_n_participants[(e - starttime).seconds // 60] -= 1

    # imos法を適用．入室・退室 → その時間に存在した人
    n = 0
    participants = []

    delta_minute = datetime.timedelta(minutes = 1)
    t = starttime
    lst_times = []
    for l in lst_n_participants:
        n += l
        participants.append(n)
        lst_times.append(t)
        t += delta_minute
    sr_participants = pd.Series(participants, index = lst_times, name = label)
    return sr_participants

def get_figure(df_participants, debug = False, fname = 'n_participants.png'):
    # seabornのフォーマットを設定
    sns.set(style = 'whitegrid')
    # sns.set_palette(sns.color_palette("Set1", 12))
    # sns.set_palette(sns.color_palette("tab20", 13))
    # sns.set_palette()

    c_list = ['#00215d', '#00468b', '#0071bc', '#589fef', '#8fd0ff', '#8c0000', '#c50827', '#ff5050', '#ff857c', '#ffb9ac', '#c9c9c9', '#999999', '#6b6b6b', '#3f3f3f', '#2a2a2a']

    # 表のフォーマットをきれいに．
    plt.rcParams['font.size'] = 13
    plt.rcParams['font.family'] = 'Helvetica'

    # figureオブジェクト，axisオブジェクトの生成
    fig = plt.figure(facecolor = 'white', dpi = 150)
    ax = fig.add_subplot(111)

    for i, (name, sr_participants) in enumerate(df_participants.iteritems()):
        # plot
        ax.plot(sr_participants.index, sr_participants, label = name, c = c_list[i])

    # x軸のformat
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M')) # x軸の表示をきれいに

    # label
    ax.set_xlabel('Time')
    ax.set_ylabel('Number of participants')

    # 凡例
    # ax.legend(edgecolor = 'None')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0, fontsize=10, edgecolor = 'None')

    plt.tight_layout()

    if debug:
        plt.show()
    else:
        fig.savefig(fname, dpi = 300)

def output_csv(df_n_participants, fname):
    td = datetime.timedelta(minutes=1)

    starttime_hour = df_n_participants.index.floor('h').min()
    endtime_hour = df_n_participants.index.ceil('h').max() + td
    
    starttime = df_n_participants.index.min()
    endtime = df_n_participants.index.max() + td
    
    def get_fill_df(l, r):
        lst = []
        t = l
        while t < r:
            lst.append(t)
            t += td
        return pd.DataFrame(np.zeros([len(lst), df_n_participants.shape[1]], dtype = np.int64), index = lst, columns = df_n_participants.columns)
    df_output = pd.concat([get_fill_df(l = starttime_hour, r = starttime), df_n_participants, get_fill_df(l = endtime, r = endtime_hour)], axis = 0)
    df_output.to_csv(fname, encoding = 'utf_8_sig')
    

if __name__ == '__main__':
    from pdb import set_trace

    dir_path = 'input'    # ディレクトリのpathを指定
    day = 3

    # csvファイル一覧を取得
    fnames_AM = []
    fnames_PM = []
    fnames = []
    for fname in os.listdir(dir_path):
        if '.csv' in fname and '{0}日目'.format(day) in fname:
            if '_AM' in fname:
                fnames_AM.append(fname)
            elif '_PM' in fname:
                fnames_PM.append(fname)
            else:
                fnames.append(fname)

    for fname_AM in copy(fnames_AM):
        fname_PM = '_'.join(fname_AM.split('_')[:-1]) + '_PM.csv'
        if fname_PM in fnames_PM:
            fnames_AM.remove(fname_AM)
            fnames_PM.remove(fname_PM)
            fname = '_'.join(fname_AM.split('_')[:-1]) + '.csv'
            pd.concat([pd.read_csv(os.path.join(dir_path, fname_AM)), pd.read_csv(os.path.join(dir_path, fname_PM))], axis = 0, ignore_index=True).to_csv(os.path.join(dir_path, fname))
            fnames.append(fname)
    else:
        fnames += fnames_AM + fnames_PM
    # ファイル名を会場番号順に並べ替える．
    fnames = sorted(list(set(fnames)), key = lambda x:int(x.split('.')[0].split('_')[0].split('Z')[-1]))
    
    # 一つのDataFrameにまとめる．
    df_n_participants = pd.concat([get_n_participants(os.path.join(dir_path, fname), label = fname.split('_')[0]) for fname in fnames], axis = 1)
    df_n_participants.fillna(0, inplace = True) # 時間の合わないところ (NaNとなってしまうところ) は参加人数0なのでfillna(0)

    # 合計値を加える
    sr_total = df_n_participants.sum(axis = 1)
    sr_total.name = 'Total'
    df_n_participants = pd.concat([sr_total, df_n_participants], axis = 1)

    # 画像の生成
    get_figure(df_n_participants, debug = True, fname = os.path.join('output', 'n_participants_day{0}.png'.format(day)))

    # データの生成
    output_csv(df_n_participants, fname = os.path.join('output', 'n_participants_day{0}.csv'.format(day)))
