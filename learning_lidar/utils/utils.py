import argparse
import csv
import logging
# %% testing multiproccesing from: https://gist.github.com/morkrispil/3944242494e08de4643fd42a76cb37ee
# import multiprocessing as mp
import os
from datetime import datetime
from functools import partial

import multiprocess as mp
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib import rc

rc('font', **{'family': 'sans-serif', 'sans-serif': ['Helvetica']})
rc('text', usetex=True)
rc('font', family='serif')
plt.rcParams['text.latex.preamble'] = r"\usepackage{amsmath}"

log_levels = {
    'critical': logging.CRITICAL,
    'error': logging.ERROR,
    'warn': logging.WARNING,
    'warning': logging.WARNING,
    'info': logging.INFO,
    'debug': logging.DEBUG
}


def create_and_configer_logger(log_name='log_file.log', level=logging.DEBUG):
    """
    Sets up a logger that works across files.
    The logger prints to console, and to log_name log file. 
    
    Example usage:
        In main function:
            logger = create_and_configer_logger(log_name='myLog.log')

        Then in all other files:
            logger = logging.getLogger(__name__)
            
        To add records to log:
            logger.debug(f"New Log Message. Value of x is {x}")
    
    Args:
        log_name: str, log file name
        
    Returns: logger
    :param log_name:
    :param level:
    """
    if type(level) is str:
        olevel = level
        level = log_levels.get(level.lower())
        if level is None:
            raise ValueError(
                f"Wrong values of log given: {olevel} \nMust be one of: {' | '.join(log_levels.keys())}")
    # TODO: make sure that once the log level is set from parser,
    #  than keep it without change, unless it is not given that keep the info level as default.
    #  Currently, the log level changes all the time from the parser level to 'info'
    # set up logging to file
    logging.basicConfig(
        filename=log_name,
        level=level,
        format='\n' + '[%(asctime)s - %(levelname)s] {%(pathname)s:%(lineno)d} -' + '\n' + ' %(message)s' + '\n',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # set up logging to console
    console = logging.StreamHandler()
    console.setLevel(level=level)
    # set a format which is simpler for console use
    formatter = logging.Formatter('[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)

    logger = logging.getLogger(__name__)
    logger.setLevel(level=level)
    return logger


def _df_split(tup_arg, **kwargs):
    split_ind, df_split, df_f_name = tup_arg
    return (split_ind, getattr(df_split, df_f_name)(**kwargs))


def df_multi_core(df, df_f_name, subset=None, njobs=-1, **kwargs):
    if njobs == -1:
        njobs = mp.cpu_count()
    pool = mp.Pool(processes=njobs)

    try:
        df_sub = df[subset] if subset else df
        splits = np.array_split(df_sub, njobs)
    except ValueError:
        splits = np.array_split(df, njobs)

    pool_data = [(split_ind, df_split, df_f_name) for split_ind, df_split in enumerate(splits)]
    results = pool.map(partial(_df_split, **kwargs), pool_data)
    pool.close()
    pool.join()
    results = sorted(results, key=lambda x: x[0])
    results = pd.concat([split[1] for split in results])
    return results


def write_row_to_csv(csv_path, msg):
    """
    Writes msg to a new row in csv_path which is a csv file.
    Logs message in logger.
    
    Args:
        csv_path: str, path to the csv file. Creates it if file doesn't exist.
        msg: list, message to write to file. Each entry in list represents a column.
    """
    with open(csv_path, 'a') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(msg)
    logger = logging.getLogger()
    logger.debug(f"Wrote to tracker{csv_path} message - {msg}")


def humanbytes(B):
    'Return the given bytes as a human friendly KB, MB, GB, or TB string'
    B = float(B)
    KB = float(1024)
    MB = float(KB ** 2)  # 1,048,576
    GB = float(KB ** 3)  # 1,073,741,824
    TB = float(KB ** 4)  # 1,099,511,627,776

    if B < KB:
        return '{0} {1}'.format(B, 'Bytes' if 0 == B > 1 else 'Byte')
    elif KB <= B < MB:
        return '{0:.2f} KB'.format(B / KB)
    elif MB <= B < GB:
        return '{0:.2f} MB'.format(B / MB)
    elif GB <= B < TB:
        return '{0:.2f} GB'.format(B / GB)
    elif TB <= B:
        return '{0:.2f} TB'.format(B / TB)


def visCurve(lData, rData, stitle=""):
    '''Visualize 2 curves '''

    fnt_size = 18
    fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(17, 6))
    ax = axes.ravel()

    for (x_j, y_j) in zip(lData['x'], lData['y']):
        ax[0].plot(x_j, y_j)
    if lData.__contains__('legend'):
        ax[0].legend(lData['legend'], fontsize=fnt_size - 6)
    ax[0].set_xlabel(lData['lableX'], fontsize=fnt_size, fontweight='bold')
    ax[0].set_ylabel(lData['lableY'], fontsize=fnt_size, fontweight='bold')
    ax[0].ticklabel_format(axis='y', style='sci', scilimits=(0, 0))
    ax[0].set_title(lData['stitle'], fontsize=fnt_size, fontweight='bold')

    for (x_j, y_j) in zip(rData['x'], rData['y']):
        ax[1].plot(x_j, y_j)
    if rData.__contains__('legend'):
        ax[1].legend(rData['legend'], fontsize=fnt_size - 6)
    ax[1].set_xlabel(rData['lableX'], fontsize=fnt_size, fontweight='bold')
    ax[1].set_ylabel(rData['lableY'], fontsize=fnt_size, fontweight='bold')
    ax[1].ticklabel_format(axis='y', style='sci', scilimits=(0, 0))
    ax[1].set_title(rData['stitle'], fontsize=fnt_size, fontweight='bold')

    fig.suptitle(stitle, fontsize=fnt_size + 4, va='top', fontweight='bold')
    fig.set_constrained_layout = True

    return [fig, axes]


def get_base_arguments(parser: argparse.ArgumentParser = None) -> argparse.ArgumentParser:
    """
    Returns the usual parameters for argument parser (station_name, start_date, end_date, plot_results, save_ds)

    :param parser: If not None, appends the arguments to the given parser
    :return:
    """
    if not parser:
        parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--station_name', type=str, default='haifa',
                        help='The station name')

    parser.add_argument('--start_date', type=datetime.fromisoformat,
                        default='2017-09-01',
                        help='The start date to use')

    parser.add_argument('--end_date', type=datetime.fromisoformat,
                        default='2017-10-31',
                        help='The end date to use')

    parser.add_argument('--plot_results', action='store_true',
                        help='Whether to plot graphs')

    parser.add_argument('--save_ds', action='store_true',
                        help='Whether to save the datasets')

    parser.add_argument("--log", default='info',
                        help=("Provide logging level. \nExample --log 'debug', \nDefault='info', "
                              f"\nMust be one of: {' | '.join(log_levels.keys())}"))

    return parser


def dt64_2_datetime(dt_64):
    date_datetime = datetime.utcfromtimestamp(dt_64.tolist() / 1e9)
    return date_datetime


def get_month_folder_name(parent_folder, day_date):
    month_folder = os.path.join(parent_folder, day_date.strftime("%Y"), day_date.strftime("%m"))
    return month_folder
