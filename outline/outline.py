from threading import main_thread
import pandas as pd
from tqdm import tqdm
from moviepy.editor import *
from glob import glob
import sys

DELTA_T = 5
FONT_SIZE = 30
TEXT_COLOR = 'red'
ADD_CAPTION = True

class CommandLineArgumentError(Exception):
    pass


def import_multiple_csv(files:list) -> pd.DataFrame:
    l = []
    for f in files:
        df = pd.read_csv(f)
        l.append(df)
    frame = pd.concat(l, axis=0, ignore_index=True)
    return frame


def s_from_str(s:str) -> int:
    if len(s.split(':')) == 3:
        ftr = [3600,60,1]
    elif len(s.split(':')) == 2:
        ftr = [60, 1]
    else:
        raise IndexError("Wrong length of time string")

    return(sum([a*b for a,b in zip(ftr, map(int,s.split(':')))]))


def main(argv:list):
    INPUT_VIDEO = argv[1]
    OUTPUT_VIDEO = argv[2]
    CSV_FILES = argv[3:]
    
    df = import_multiple_csv(CSV_FILES).sort_values('Time')

    df = df.sort_values('Time')
    df = df.reset_index(drop=True)
    
    
    # Select only necessary bits of DataFrame
    df_filtered = df.loc[((df['Action'] == 'Kick') & ((df['Result'] == 'Goal') | (df['Result'] == 'Save') | (df['Result'] == 'Autogoal'))) | ((df['Action'] == 'Tackle') & (df['Opposite'] == 1)) | ((df['Action'] == 'Interception') & (df['Opposite'] == 1)) | ((df['Action'] == 'Key Pass') & (df['Result'] == 'Success')) | ((df['Action'] == 'Dribble') & (df['Result'] == 'Success'))]
    
    
    df = df_filtered
    df['left'] = df.apply(lambda x: max(0, s_from_str(x['Time']) - DELTA_T), axis=1)
    df['right'] = df.apply(lambda x: max(0, s_from_str(x['Time']) + DELTA_T + 1), axis=1)

    df['Caption'] = df.apply(lambda x: "{} - {} by team {}, player {}".format(x['Time'], x['Action'], int(x['Team']), int(x['Player'])), axis=1)
    iix = pd.IntervalIndex.from_arrays(df.left, df.right, closed='both')

    clip = VideoFileClip(INPUT_VIDEO)
    duration = int(clip.duration)

    texts = {}
    for i in range(duration):
        texts[i] = '\n'.join(df[iix.overlaps(pd.Interval(i, i, closed='both'))]['Caption'].tolist())

    
    if ADD_CAPTION:        
        textclips = [clip]
        print("Adding text to video...")
        for i in tqdm(range(duration)):
            if texts[i] != '':
                txt_clip = TextClip(texts[i], fontsize = FONT_SIZE, color = TEXT_COLOR)
                txt_clip = txt_clip.set_pos('top').set_duration(1.0).set_start(i)
                textclips.append(txt_clip)
                
        print("Composing videoclip with text captions")
        video = CompositeVideoClip(textclips) 
    else:
            video = clip


    cuts = []
    clip_ongoing = False
    current_clip_start = None
    current_clip_end = None

    print("Cutting highlights...")
    for i in tqdm(range(duration)):
        if texts[i] != '':
            if not clip_ongoing:
                clip_ongoing = True
                current_clip_start = i
        else:
            if clip_ongoing:
                current_clip_end = i
                cuts.append(video.subclip(current_clip_start, current_clip_end))
                clip_ongoing = False
                cuts.append(video.subclip(i, i+1))
                
    cut_video = concatenate_videoclips(cuts)

    print("Writing video")
    cut_video.write_videofile(OUTPUT_VIDEO, audio=True, bitrate='6000k')

if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise CommandLineArgumentError("Wrong number of command-line arguments, must be at least 3, provided {}".format(len(sys.argv) - 1))
    else:
        main(sys.argv)