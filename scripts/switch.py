#!/usr/bin/python2.7

import i3
outputs = i3.get_outputs()

# set current workspace to output 0
i3.workspace(outputs[0]['current_workspace'])

# move it to the other output
i3.command('move', 'workspace to output right')

# rinse and repeat
i3.workspace(outputs[2]['current_workspace'])
i3.command('move', 'workspace to output right')
