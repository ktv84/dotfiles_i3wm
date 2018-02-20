#!/usr/bin/python3.5
import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

import sys
import signal

LEN_ARGS = len(sys.argv)
POSITION_X = int(sys.argv[1]) if LEN_ARGS > 1 else None
POSITION_Y = int(sys.argv[2]) if LEN_ARGS > 2 else None
BAR_HEIGHT = int(sys.argv[3]) if LEN_ARGS > 3 else 15

# This css is used mainly by music-control but
# I may keep adding to it and its nice to have
# it in specific place
css = """
.left-semi-circle {
  border-top-left-radius: 25px;
  border-bottom-left-radius: 25px;
}

.right-semi-circle {
  border-top-right-radius: 25px;
  border-bottom-right-radius: 25px;
}

.circular {
  margin-top: 10px;
}

.margin-fix {
  margin-top: 15px;
}
"""

style_provider = Gtk.CssProvider()
style_provider.load_from_data(str.encode(css))
Gtk.StyleContext.add_provider_for_screen(
  Gdk.Screen.get_default(),
  style_provider,
  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
)

def get_window_position_by_args(display):
  """
    If the script was given arguments, it will use those as the position,
    if not it will find the primary monitor and the middle of that
    as the position
  """
  if POSITION_X is not None and POSITION_Y is not None:
    return POSITION_X, POSITION_Y

  primary_monitor = display.get_primary_monitor()
  workarea = primary_monitor.get_workarea()

  return workarea.x + workarea.width / 2, workarea.y + workarea.height

class BlocksWindow(Gtk.Window):
  """
    This class represents a BlocksWindow that is to be used together with i3 as
    a way of increasing the amount of information and interaction that can
    be done. Since the i3blocks is only limited to showing a certain amount of
    information and cannot open menus etc, I created this class
    to help with that.

    This expected to be the base class of any windows that are made for i3bar
    as it makes sure to poisition the window just above the bar where the bar
    was clicked.

    In addition, it also a special way of exiting. Most GTK programs require
    you to either click `X` or a button. This program will exit when either;

    1. User clicks `Esc`
    2. User moves the mouse outside of the window

    The latter option will only happen if the mouse has been inside the window
    in the first place.

    The window can be told where to render (and in most cases you should) by
    giving it X and Y coordinates (absolute values). Another third argument,
    which defaults to 15, is the height of the bar.

    If no coordinates are given, it will find the middle of the primary monitor
    and place it there (though low on the monitor)
  """

  def __init__(self, width=200, height=100):

    Gtk.Window.__init__(self)
    display = Gdk.Display.get_default()

    # Get the absolute coordinates and bar height from arguments
    self.x, self.y = get_window_position_by_args(display)

    self.width = width
    self.height = height

    # Set some default values for the window, since we
    # want to display it as kind of a popup-window
    self.set_border_width(10)
    self.set_default_size(self.width, self.height)
    self.set_resizable(False)
    self.set_decorated(False)
    self.set_skip_pager_hint(True)
    self.set_skip_taskbar_hint(True)
    self.set_keep_above(True)

    # Retrive information about the current monitor that
    # the window will be shown on as these are used everytime
    # the window resizes.
    self.monitor = display.get_monitor_at_point(self.x, self.y)
    self.workarea = self.monitor.get_workarea()

    self.connect("delete-event", Gtk.main_quit)
    self.connect("check_resize", self.on_resize)
    self.connect('leave-notify-event', self.on_leave)

    # if control-c is pressed, we also exit
    signal.signal(signal.SIGINT, signal.SIG_DFL)

  def show(self):
    """
      This overrides the default show as it requires it to also set
      the correct position of the window
    """
    Gtk.Window.show(self)
    self.set_position()

  def is_inside_window(self, x, y):
    """
      Checks whether a given `x` and `y` coordinate is within the window
    """
    rect = self.get_allocation()

    top_x, top_y = self.get_position()
    bottom_x, bottom_y = self.x + rect.width, self.y + rect.height

    return top_x < x and bottom_x > x and top_y < y and bottom_y > y

  def find_optimal_position(self):
    """
      Tries to find the optimal position for the window on the monitor
      that it was told to render on.

      It will try to place itself so that the middle of width is exactly where
      the mouse click happened, but when doing so, it will make sure
      to take the monitor size into consideration.
    """
    rect = self.get_allocation()

    x = min(self.workarea.width - rect.width / 2, self.x - self.workarea.x)
    y = min(self.workarea.height, self.y - self.workarea.y) - BAR_HEIGHT - 5

    if y - rect.height < 0:
      y = rect.height + BAR_HEIGHT + 10

    return self.workarea.x + x, self.workarea.y + y

  def get_position(self):
    """
      Returns the position of the window
    """
    rect = self.get_allocation()
    x, y = self.find_optimal_position()
    return (x - rect.width / 2, y - rect.height)

  def set_position(self, x=None, y=None):
    """ Sets the position to `x` and `y`. If `x` or `y` is not defined,
        it will use `get_position` to set itself.
    """
    if x is None or y is None:
      x, y = self.get_position()

    self.move(x, y)

  def on_resize(self, _):
    """ Handles resizing events, which will happen even though the user
        isnt allowed to resize the window
    """
    self.set_position()

  def on_leave(self, widget, event):
    """ Handles on leave events. On leave events happen quite often and
        it does not neccessarily mean that mouse moved outside the window.

        It can, for example, mean some of the following things;

        1. User moused over a widget
        2. User moused over a window within the window

        Due to this, we have to listen for `NONLINEAR` leave events,
        but even these can be untrustworthy. For instance, if a different
        window is within the borders of this window, it will detect it
        as a `NONLINEAR` leave event. Due to this, we also have to make sure
        that the mouse actually left the window by checking coordinates up
        against the window coordinates.

        TODO: Check grab broken in GDK to fix this
    """
    is_leave_notify = event.detail == Gdk.NotifyType.NONLINEAR

    if is_leave_notify and not self.is_inside_window(event.x_root, event.y_root):
      Gtk.main_quit()
