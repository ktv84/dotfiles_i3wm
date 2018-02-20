import gi

from gi.repository import Gtk
from gi.repository import Gdk

class Completion():
  """
    This class is a half redefintion of the EntryCompletion widget that
    GTK exposes. The reason for not using that widget is that the
    completion menu would pop up anywhere it would like.

    For instance, if you had 250 songs, it would show all it could
    fit on your monitor. If you then moved your mouse to that list
    and kept writing, the list would get shorted and get resized. This
    would lead to `window` to exit as it technically lost focus (due to i3's
    grab using mouse).

    Since GTK has no way of either; Limting the height of the completion
    menu or limit to be inside the parent window, I decided to implement
    my own.

    This version is more simplistic than the EntryCompletion as it
    only accepts lists of strings (no tuples, no rows etc).

    In addition, it will do full match of the string, meaning if
    you have the song name:
    `In Flames - Where the Dead Ships Dwell` and you wrote:
    `in dead ships` it would match on the above string seeing as
    `in`, `dead` and `ships` are in it. (Doesnt care about case)

    Simple, but useful. Will never be larger than the window itself.
    """
  def __init__(self, window, entry):
    self.entry = entry
    self.entry_window = window

    # Create the window that should hold the completion menu since
    # it has to cover other widgets
    self.window = Gtk.Window(Gtk.WindowType.POPUP)
    self.window.set_resizable(False)
    self.window.move(50, 50)
    self.window.set_type_hint(Gdk.WindowTypeHint.COMBO)

    # Frame for pretty ness
    self.frame = Gtk.Frame()
    self.frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
    self.frame.show()
    self.window.add(self.frame)

    # Scrollable window since we can have lots of completions
    self.scroll = Gtk.ScrolledWindow()
    self.scroll.set_min_content_height(0)
    self.scroll.set_max_content_width(200)
    self.frame.add(self.scroll)

    # The tree view itself that can hold a list of strings
    self.model = Gtk.ListStore(str)
    renderer = Gtk.CellRendererText()
    self.column = Gtk.TreeViewColumn('', renderer, text=0)
    self.view = Gtk.TreeView(self.model)
    self.view.set_headers_visible(False)
    self.view.append_column(self.column)
    self.scroll.add(self.view)

    self.selected = 0
    self.elements = []
    self.previous_height = 0
    self.selection = self.view.get_selection()
    self.is_hidden = True

    # Add the key-press-event to detect `up`, `down` and `return`
    # so we can handle them approriately
    self.entry.connect('key-press-event', self.on_keypress)

    # When text changes, we change our tree view
    self.entry.connect('changed', self.on_typing)

  def on_keypress(self, widget, event):
    """
      This handles some of the keypresses that happens on the
      entry that is bound to this completion menu.

      It will currently only handle `arrow_up`, `arrow_down` and `return`.
      The arrow buttons are used for navigating the completion menu
      (this can also be done with the mouse but this requires no code)

      The return button is used to select an entry within the completion menu

      Any other values are sent to the next handlers
    """
    self.show()

    length = self.model.iter_n_children()
    returnVal = False

    # Go above max length === go back to 0
    # Go below 0 and you are back to the entry box
    if event.keyval == Gdk.KEY_Down or event.keyval == Gdk.KEY_KP_Down:
      self.selected = self.selected + 1 if self.selected < length else 0
      returnVal = True
    elif event.keyval == Gdk.KEY_Up or event.keyval == Gdk.KEY_KP_Up:
      self.selected = self.selected - 1
      returnVal = True

    # If we click enter we want to get the selected entry
    # and move the text pointer to the end of the word
    # before we hide the completion menu
    if event.keyval == Gdk.KEY_Return:
      _, it = self.selection.get_selected()
      if it:
        self.entry.set_text(self.model[it][0])
        self.entry.set_position(-1)
        returnVal = True
        self.hide()

    # Move focus to entry box if the selection is below 0, else
    # set new selection. Only one selection is allowed
    if self.selected < 0:
      self.selected = 0
      self.entry.grab_focus()
    else:
      path = Gtk.TreePath.new_from_indices([self.selected])
      self.view.set_cursor(path, self.column, True)

    return returnVal

  def on_typing(self, widget):
    """
      This function is called whenever the user writes text into the entry
      field, which should make us readjust our view based on the text.
      This does this by updating the model and therefore updating the
      view that is shown in the completion menu
    """
    text = widget.get_text().lower()
    split = text.split()
    matches = [element
               for element in self.elements
               if len(split) == len([x for x in split if x in element.lower()])]
    self.update_model(matches)
    self.update_height()
    self.selection.unselect_all()
    self.selection.select_path(Gtk.TreePath.new_first())

  def update_list(self, elements):
    """Sets a new list of strings to use as completion"""
    self.elements = elements
    self.update_model(elements)

  def update_model(self, elements):
    """ Updates the model by appending the list of elements given"""
    self.model.clear()
    [self.model.append([x]) for x in elements]

  def update_height(self):
    """
      Since the height of the completion is kind of the whole point of
      using this compared to the GTK version, this function is kind of
      important.

      It will set the size determined by how many elements are
      inside the model, but it will never go outside the parent
      window of the entry.

      It can therefore be shorter, if there are few elements in the model
    """
    length = self.model.iter_n_children()

    rect = self.column.cell_get_size()
    height = rect.height * length

    height = min(height, self.scroll_height)

    if height == self.previous_height:
      return

    if height > self.previous_height:
      self.scroll.set_max_content_height(height)
      self.scroll.set_min_content_height(max(height - 10, 0))
    elif height < self.previous_height:
      self.scroll.set_min_content_height(max(height - 10, 0))
      self.scroll.set_max_content_height(height)

    self.previous_height = height

  def hide(self):
    """ Lets hide """
    self.window.hide()

  def show(self):
    """
      Shows the widget and window and adjusts the position
      to be below the entry field. Also updates the height
    """
    window_x, window_y = self.entry_window.get_position()
    window_alloc = self.entry_window.get_allocation()
    entry_alloc = self.entry.get_allocation()

    x = window_x + entry_alloc.x
    y = window_y + entry_alloc.y + entry_alloc.height

    self.scroll_height = window_alloc.height - (entry_alloc.y + entry_alloc.height)
    self.scroll_width  = entry_alloc.width

    self.scroll.set_max_content_width(self.scroll_width)
    self.scroll.set_min_content_width(self.scroll_width)

    self.update_height()
    self.window.move(x, y)
    self.window.show_all()
