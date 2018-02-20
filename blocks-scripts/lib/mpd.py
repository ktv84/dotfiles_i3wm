"""
  This module defines a lot of helper functions and classes
  when dealing with MPC. Everything is encapsulated into a nice
  MPC class that can be instanciated.

  MPC class has an update_song_time, which should, if possible,
  be executed every second through a loop / threading of some
  kind. When the song time gets above the maximum for the song,
  it will update the information in the class as it assumes
  that a new song is now playing.
"""
import subprocess
import re
import math

class SongTime():
  """
    Wrapper class for song time. Expects current and end to
    be of the format `00:00`.
    Can be used to keep track of the song status
  """
  def __init__(self, current, end):
    current_min, current_sec = [int(x) for x in current.split(':')]
    end_min, end_sec = [int(x) for x in end.split(':')]

    self.current = current_min * 60 + current_sec
    self.end = end_min * 60 + end_sec

  def increase(self, seconds=1):
    """Increases the current status by `seconds`"""
    self.current = self.current + seconds

    return self.current >= self.end

  def as_progress_string(self):
    """Returns the status as a strong of 00:00 / 00:00"""
    cm = math.floor(self.current / 60)
    cs = self.current - (cm * 60)
    em = math.floor(self.end / 60)
    es = self.end - (em * 60)

    return '%s:%s / %s:%s' % (str(cm).zfill(2),
                              str(cs).zfill(2),
                              str(em).zfill(2),
                              str(es).zfill(2))

  def as_fraction(self):
    """Returns how far the song is along as a fraction, ex 0.85"""
    if self.end == 0:
      return 0
    return self.current / self.end

DEFAULT_VALUES = {
  'artist': 'None',
  'song': 'None',
  'status': 'Stopped',
  'num': 0,
  'num_of': 0,
  'song_time': SongTime('0:00', '0:00'),
  'progress_percent': 0,
  'volume': 0,
  'repeat': False,
  'random': False,
  'single': False,
  'consume': False
}

LEGAL_MODIFIERS = [
  'random',
  'single',
  'consume',
  'repeat'
]

def _remove_ws(s):
  return re.sub('\s+', ' ', s)

def _parse_output(output):
  """
    Parses the output of mpc from a string to a more useful format of
    a dictionary. The output format has the key/type of:

    `artist`, str           - Name of the artist
    `song`, str             - Name of the song
    `status`, str           - playing or paused
    `num`, int              - Number of song
    `num_of`, int           - Maximum number of songs in playlist
    `song_time`, SongTime   - The current and end of song as a encapsulated class
    `repeat`, bool          - Whether the repeat flag is set or not
    `random`, bool          - Whether the random flag is set or not
    `single`, bool          - Whether the single flag is set or not
    `consume`, bool         - Whether the consume flag is set or not

    Should an error occur or an mpd server is not running, it will
    give default values which should be of the same types as above,
    but won't be any informative.
    """
  if 'mpd error:' in output:
    return DEFAULT_VALUES

  lines = [x for x in output.split('\n') if x != '']

  try:
    artist, song = [x.strip() for x in lines[0].split('-', 1)]
    status, num, progress, _ = _remove_ws(lines[1]).split(' ')
  except Exception:
    artist, song = ('None', 'None')
    status, num, progress = 'Stopped', '#0/0', '00:00/00:00'
  volume, repeat, random, single, consume = _remove_ws(
      re.sub('\w+:', '', lines[len(lines)-1]).strip()).split(' ')

  num, num_of = num.split('/')
  start_time, end_time = progress.split('/')

  return {
    'artist': artist,
    'song': song,
    'status': re.sub('\[|\]', '', status),
    'num': int(num.replace('#', '')),
    'num_of': int(num_of),
    'song_time': SongTime(start_time, end_time),
    'volume': int(volume.replace('%', '')),
    'repeat': repeat == 'on',
    'random': random == 'on',
    'single': single == 'on',
    'consume': consume == 'on'
  }

def run_mpc(msg):
  """ Runs the `mpc` program with the msg """
  if not isinstance(msg, list):
    msg = [msg]

  msg = ['mpc'] + msg
  try:
    output = subprocess.check_output(
        msg,
        stderr=subprocess.DEVNULL).decode('utf-8')
  except subprocess.CalledProcessError as e:
    output = 'mpd error:'

  return output

class Mpc():
  def __init__(self):
    self.update()

  def update(self):
    """
      Sends a status message to mpc retrieving current status
      and updating this class
    """
    self._set_info(run_mpc('status'))

  def _set_info(self, mpc_info):
    """
      Private function that is used to update
      the information stored in the class by querying
      MPC
    """
    if isinstance(mpc_info, str):
      mpc_info = _parse_output(mpc_info)

    for key, value in mpc_info.items():
      setattr(self, key, value)

  def get_name_with_status(self):
    """
      Returns the name of the artist, song with current status in format:
      ARISTNAME - SONGNAME [paused]
      or
      ARISTNAME - SONGNAME [01:23 / 04:56]
    """

    if self.is_paused():
      return '%s - %s [paused]' % (self.artist, self.song)

    return '%s - %s [%s]' % (self.artist, self.song, self.song_time.as_progress_string())

  def update_song_time(self, seconds=1):
    """Updates the song time stored by adding a second"""
    if not self.is_playing():
      return

    if self.song_time.increase(seconds):
      self.update()

  def toggle_status(self):
    """Sets the status to playing if paused, otherwise pauses the song"""
    self.status = 'paused' if self.status == 'playing' else 'playing'
    run_mpc('toggle')

  def is_paused(self):
    """Returns true if it is paused"""
    return self.status == 'paused'

  def is_playing(self):
    """Returns true if it is playing something"""
    return self.status == 'playing'

  def get_playlist(self):
    """
      Retrieves the current playlist mpc and splits it
      into a list of dictionaries with `name` and `index` keys. The
      index are later used to play the song
    """
    output = run_mpc('playlist')
    return [{'name': name, 'index': i+1} for i, name in enumerate(output.split('\n'))]

  def play(self, song):
    """
      Starts playing a song. Expects the `song` parameter to either
      be an integer indicating the number of the song or it expects
      a dictionary with `index` to be a key within it with an
      integer as the number of the song
    """

    if isinstance(song, dict) and 'index' in song:
      run_mpc(['play', str(song['index'])])
    elif instance(song, int):
      run_mpc(['play', str(song)])

    self.update()

  def toggle_modifier(self, name):
    """
      Toggles the modifier (random, consume, single or repeat)
    """
    self.set_modifier(name, not self.get_modifier(name))

  def get_modifier(self, name):
    """
      Retrieves the modifier by its name, which is either `random`,
      `single`, `consume` or `repeat`. All other names will throw errors
    """
    if name not in LEGAL_MODIFIERS:
      msg = 'Illegal modifier %s, expected one of [%s]'
      raise Exception(msg % (name, ', '.join(LEGAL_MODIFIERS)))

    return getattr(self, name)

  def set_modifier(self, name, value):
    """
      Sets the `name` modifier to `value`. Name should be either `random`,
      `single`, `consume` or `repeat`. All other names will throw errors

      The `value` will be checked to be truthish
    """
    if name not in LEGAL_MODIFIERS:
      msg = 'Illegal modifier %s, expected one of [%s]'
      raise Exception(msg % (name, ', '.join(LEGAL_MODIFIERS)))

    run_mpc([name, 'on' if value else 'off'])
    setattr(self, name, value)

  def set_volume(self, vol):
    """
      Sets the volume of MPC/MPD where `vol` is an integer between 0 and 100
    """
    if vol > 100:
      vol = 100
    if vol < 0:
      vol = 0
    if vol != self.volume:
      self.volume = vol
      run_mpc(['volume', str(self.volume)])

  def next_song(self):
    """Goes forward and starts playing the next song"""
    run_mpc(['next'])
    self.update()

  def prev_song(self):
    """Goes backwards and starts playing the previous song"""
    run_mpc(['prev'])
    self.update()


