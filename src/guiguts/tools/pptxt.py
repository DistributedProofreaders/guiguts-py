import argparse
import sys
import os
import platform
import re

########################################################
# pptxt.py
# Python author: Quentin Campbell (DP:qgc) - 2023
# Perl author: Roger Franks (DP:rfrank) - 2009
# Go author: Roger Franks (DP:rfrank) - 2020
# Last edit: 12-dec-2023
########################################################


def decorate(string, list_of_tuples, style):
    class color:
        RED = "\033[91m"
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        BOLD = "\033[1m"
        ITALIC = "\033[3m"
        UNDERLINE = "\033[4m"
        END = "\033[0m"

    class super:
        TWO = "²"
        THREE = "³"
        FOUR = "⁴"
        FIVE = "⁵"

    # Don't assume the tuples in the passed in list are sorted.
    # Make sure as they need to be for the sanity checks below.

    list_of_slices = list_of_tuples.copy()
    list_of_slices.sort()

    # There should be one or more tuples (slice_start, slice_length)
    # in list. If list is empty just returm original string and exit.

    if len(list_of_slices) == 0:
        return string

    # At least one tuple in list so we have work to do.

    # However before we get going various things need to be initialised
    # outside of the main (slices) loop.

    #############################################
    # For the 'pointer' and 'dash' style we need:
    #############################################

    # A separate marker string which will eventually contain one
    # or more pointers/dashes and filler characters (' ').

    marker_string = ""

    # The pointer character to use.

    pointer = "^"

    # The dash character to use.

    dash = "-"  # hyphen

    # A count of filler characters and pointer/dash characters added
    # so far to the marker string

    fill_level = 0

    #################################################################
    # For the inline highlighting style (colors, bold, etc.) we need:
    #################################################################

    # A flag that tells us whether we have to do anything before we
    # return the modified string.

    inline = False

    # Pointer to keep track of any unhighlighted slices of the string
    # that we need to copy to the new string we are building up.

    ptr = 0

    # The new string that will contain unhighlighted parts and highlighted
    # parts that are bracketed by 'color commands'.

    newstring = ""

    #################################################################
    # For the inline superscipt style we need:
    #################################################################

    # A mutable version of the string so that we can change characters
    # in-place. Convert the string to a list of characters. It will be
    # changed back to a string before returning.

    muttable_string = []

    for ch in string:
        muttable_string.append(ch)

    # A flag that tells us whether we have to do anything before we
    # return the (possibly) modified string.

    supers = False

    #################################################################
    # For the 'do nothing' style ('')
    #################################################################

    dont_decorate = False

    ##############################
    # End of styles initialisation
    ##############################

    # Here the main loop that determines which parts of the string
    # are to be highlighted then highlights them.

    # For the sanity checks carried out below we need to keep
    # track of the position of the last character highlighted
    # in the loop.

    last_highlight_position = -1

    for tple in list_of_slices:
        # A tuple contains two values:
        #   1. The position in the string where a slice starts;
        #   2. The length of the slice. E.g. Will be 1 if a
        #      single character to be highlighted.

        slice_start = tple[0]
        slice_length = tple[1]

        # Sanity checks on string slices to be highlighted:
        #
        # 1. Start position of a slice should not be before start
        #    of string and not after its last character.
        #
        # 2. Start position + length of slice (i.e. number of
        #    characters to be highlighted from start position
        #    onwards) should not exceed the length of string.
        #
        # 3. Start position of slice is at or before the position
        #    of the last character highlighted; i.e. the current
        #    tuple is overwriting at least one character already
        #    highlighted by a previous tuple.
        #
        # In all cases quietly ignore tuple and look at next one.

        if slice_start < 0 or slice_start >= len(string):
            continue

        if slice_start + slice_length > len(string):
            continue

        if slice_start <= last_highlight_position:
            continue

        last_highlight_position = slice_start + slice_length - 1

        ##################################################
        # Decorate the string slice in the required style.
        ##################################################

        if style == "pointer":
            # Add filler ' ' characters if needed

            while fill_level < slice_start:
                marker_string = marker_string + " "
                fill_level += 1

            # Now add required number of pointer characters ('^')

            for pointers_needed in range(slice_start, slice_start + slice_length):
                marker_string = marker_string + pointer
                fill_level += 1

        elif style == "super":
            # This is in-line highlighting by replacement with a different
            # character. No separate marker string is needed as, for example,
            # with the 'pointer' or 'dash' styles.

            supers = True

            # If the character to be highlighted is a digit then replace it
            # in the string with that digit as a superscript. If the character
            # is not a digit then leave the character as is.

            for posn in range(slice_start, slice_start + slice_length):
                if string[posn : posn + 1] == "2":
                    muttable_string[posn] = super.TWO
                elif string[posn : posn + 1] == "3":
                    muttable_string[posn] = super.THREE
                elif string[posn : posn + 1] == "4":
                    muttable_string[posn] = super.FOUR
                elif string[posn : posn + 1] == "5":
                    muttable_string[posn] = super.FIVE
                else:
                    # Leave character in muttable_string unchanged

                    pass

            else:
                # We may get here for the first tuple but in that case the slice
                # it defines does not start at first character in the string.

                # If there are any un-highlighted characters in the string between
                # the start of this slice and the end of the previous highlighted
                # slice, or the start of the string if this is the first tuple,
                # add those un-higlighted characters to the new string then add
                # the latest slice to be highlighted with its 'color commands'.

                newstring = newstring + string[ptr:slice_start]
                ptr = slice_start
                newstring = (
                    newstring
                    + color.RED
                    + string[slice_start : slice_start + slice_length]
                    + color.END
                )
                ptr = slice_start + slice_length

                # NB If any un-highlighted characters at end of string, they will
                #    be appended to newstring in the tidying up done when the main
                #    tuples loop is exited, just before returning.

        elif style == "dash":
            # Add filler ' ' characters if needed

            while fill_level < slice_start:
                marker_string = marker_string + " "
                fill_level += 1

            # Now add required number of dash characters - hyphen

            for pointers_needed in range(slice_start, slice_start + slice_length):
                marker_string = marker_string + dash
                fill_level += 1

        elif style == "red":
            # This is in-line highlighting. No separate marker string
            # is needed as, for example, with the 'pointer' or 'dash styles.

            inline = True

            # It's done by inserting 'color commands' before and after each
            # slice to be highlighted in the string. A slice is defined by
            # a tuple from the list of tuples supplied in the call. The
            # string passed in from the call is not changed. Instead a new
            # string is built up and added to by each tuple. It will contain
            # at the end of the tuple loop any unhighlghted slices plus all
            # highlighted slices in the correct order.

            if slice_start == 0:
                # The start of the slice defined by the tuple starts at the first
                # character in the string.
                #
                # Because of the sanity checks carried out on entering the function
                # this can only be true for the first tuple.

                newstring = (
                    color.RED
                    + string[slice_start : slice_start + slice_length]
                    + color.END
                )
                ptr = slice_start + slice_length

            else:
                # We may get here for the first tuple but in that case the slice
                # it defines does not start at first character in the string.

                # If there are any un-highlighted characters in the string between
                # the start of this slice and the end of the previous highlighted
                # slice, or the start of the string if this is the first tuple,
                # add those un-higlighted characters to the new string then add
                # the latest slice to be highlighted with its 'color commands'.

                newstring = newstring + string[ptr:slice_start]
                ptr = slice_start
                newstring = (
                    newstring
                    + color.RED
                    + string[slice_start : slice_start + slice_length]
                    + color.END
                )
                ptr = slice_start + slice_length

        elif style == "green":
            # This is in-line highlighting. No separate marker string
            # is needed as, for example, with the 'pointer' or 'dash styles.

            inline = True

            # It's done by inserting 'color commands' before and after each
            # slice to be highlighted in the string. A slice is defined by
            # a tuple from the list of tuples supplied in the call. The
            # string passed in from the call is not changed. Instead a new
            # string is built up and added to by each tuple. It will contain
            # at the end of the tuple loop any unhighlghted slices plus all
            # highlighted slices in the correct order.

            if slice_start == 0:
                # The start of the slice defined by the tuple starts at the first
                # character in the string.
                #
                # Because of the sanity checks carried out on entering the function
                # this can only be true for the first tuple.

                newstring = (
                    color.GREEN
                    + string[slice_start : slice_start + slice_length]
                    + color.END
                )
                ptr = slice_start + slice_length

            else:
                # We may get here for the first tuple but in that case the slice
                # it defines does not start at first character in the string.

                # If there are any un-highlighted characters in the string between
                # the start of this slice and the end of the previous highlighted
                # slice, or the start of the string if this is the first tuple,
                # add those un-higlighted characters to the new string then add
                # the latest slice to be highlighted with its 'color commands'.

                newstring = newstring + string[ptr:slice_start]
                ptr = slice_start
                newstring = (
                    newstring
                    + color.GREEN
                    + string[slice_start : slice_start + slice_length]
                    + color.END
                )
                ptr = slice_start + slice_length

        elif style == "yellow":
            # This is in-line highlighting. No separate marker string
            # is needed as, for example, with the 'pointer' or 'dash styles.

            inline = True

            # It's done by inserting 'color commands' before and after each
            # slice to be highlighted in the string. A slice is defined by
            # a tuple from the list of tuples supplied in the call. The
            # string passed in from the call is not changed. Instead a new
            # string is built up and added to by each tuple. It will contain
            # at the end of the tuple loop any unhighlghted slices plus all
            # highlighted slices in the correct order.

            if slice_start == 0:
                # The start of the slice defined by the tuple starts at the first
                # character in the string.
                #
                # Because of the sanity checks carried out on entering the function
                # this can only be true for the first tuple.

                newstring = (
                    color.YELLOW
                    + string[slice_start : slice_start + slice_length]
                    + color.END
                )
                ptr = slice_start + slice_length

            else:
                # We may get here for the first tuple but in that case the slice
                # it defines does not start at first character in the string.

                # If there are any un-highlighted characters in the string between
                # the start of this slice and the end of the previous highlighted
                # slice, or the start of the string if this is the first tuple,
                # add those un-higlighted characters to the new string then add
                # the latest slice to be highlighted with its 'color commands'.

                newstring = newstring + string[ptr:slice_start]
                ptr = slice_start
                newstring = (
                    newstring
                    + color.YELLOW
                    + string[slice_start : slice_start + slice_length]
                    + color.END
                )
                ptr = slice_start + slice_length

        elif style == "bold":
            # This is in-line highlighting. No separate marker string
            # is needed as, for example, with the 'pointer' or 'dash styles.

            inline = True

            # It's done by inserting 'color commands' before and after each
            # slice to be highlighted in the string. A slice is defined by
            # a tuple from the list of tuples supplied in the call. The
            # string passed in from the call is not changed. Instead a new
            # string is built up and added to by each tuple. It will contain
            # at the end of the tuple loop any unhighlghted slices plus all
            # highlighted slices in the correct order.

            if slice_start == 0:
                # The start of the slice defined by the tuple starts at the first
                # character in the string.
                #
                # Because of the sanity checks carried out on entering the function
                # this can only be true for the first tuple.

                newstring = (
                    color.BOLD
                    + string[slice_start : slice_start + slice_length]
                    + color.END
                )
                ptr = slice_start + slice_length

            else:
                # We may get here for the first tuple but in that case the slice
                # it defines does not start at first character in the string.

                # If there are any un-highlighted characters in the string between
                # the start of this slice and the end of the previous highlighted
                # slice, or the start of the string if this is the first tuple,
                # add those un-higlighted characters to the new string then add
                # the latest slice to be highlighted with its 'color commands'.

                newstring = newstring + string[ptr:slice_start]
                ptr = slice_start
                newstring = (
                    newstring
                    + color.BOLD
                    + string[slice_start : slice_start + slice_length]
                    + color.END
                )
                ptr = slice_start + slice_length

        elif style == "italic":
            # This is in-line highlighting. No separate marker string
            # is needed as, for example, with the 'pointer' or 'dash styles.

            inline = True

            # It's done by inserting 'color commands' before and after each
            # slice to be highlighted in the string. A slice is defined by
            # a tuple from the list of tuples supplied in the call. The
            # string passed in from the call is not changed. Instead a new
            # string is built up and added to by each tuple. It will contain
            # at the end of the tuple loop any unhighlghted slices plus all
            # highlighted slices in the correct order.

            if slice_start == 0:
                # The start of the slice defined by the tuple starts at the first
                # character in the string.
                #
                # Because of the sanity checks carried out on entering the function
                # this can only be true for the first tuple.

                newstring = (
                    color.ITALIC
                    + string[slice_start : slice_start + slice_length]
                    + color.END
                )
                ptr = slice_start + slice_length

            else:
                # We may get here for the first tuple but in that case the slice
                # it defines does not start at first character in the string.

                # If there are any un-highlighted characters in the string between
                # the start of this slice and the end of the previous highlighted
                # slice, or the start of the string if this is the first tuple,
                # add those un-higlighted characters to the new string then add
                # the latest slice to be highlighted with its 'color commands'.

                newstring = newstring + string[ptr:slice_start]
                ptr = slice_start
                newstring = (
                    newstring
                    + color.ITALIC
                    + string[slice_start : slice_start + slice_length]
                    + color.END
                )
                ptr = slice_start + slice_length

        elif style == "underline":
            # This is in-line highlighting. No separate marker string
            # is needed as, for example, with the 'pointer' or 'dash styles.

            inline = True

            # It's done by inserting 'color commands' before and after each
            # slice to be highlighted in the string. A slice is defined by
            # a tuple from the list of tuples supplied in the call. The
            # string passed in from the call is not changed. Instead a new
            # string is built up and added to by each tuple. It will contain
            # at the end of the tuple loop any unhighlghted slices plus all
            # highlighted slices in the correct order.

            if slice_start == 0:
                # The start of the slice defined by the tuple starts at the first
                # character in the string.
                #
                # Because of the sanity checks carried out on entering the function
                # this can only be true for the first tuple.

                newstring = (
                    color.UNDERLINE
                    + string[slice_start : slice_start + slice_length]
                    + color.END
                )
                ptr = slice_start + slice_length

            else:
                # We may get here for the first tuple but in that case the slice
                # it defines does not start at first character in the string.

                # If there are any un-highlighted characters in the string between
                # the start of this slice and the end of the previous highlighted
                # slice, or the start of the string if this is the first tuple,
                # add those un-higlighted characters to the new string then add
                # the latest slice to be highlighted with its 'color commands'.

                newstring = newstring + string[ptr:slice_start]
                ptr = slice_start
                newstring = (
                    newstring
                    + color.UNDERLINE
                    + string[slice_start : slice_start + slice_length]
                    + color.END
                )
                ptr = slice_start + slice_length

        elif style == "none":
            # Return the string unchanged as no decoaration specified. Use
            # where an option to a tool allows for decoration/no decoration.

            dont_decorate = True

        else:
            # Catch-all. Quietly return the string unchanged.

            dont_decorate = True

    # Here when list of tuples exhausted.

    if inline:
        # An inline style such as color, bold, etc. Before returning
        # the new string we have built up with its inserted 'color
        # commands', append any remaining un-highlighted characters
        # from the original string.

        if ptr < len(string):
            newstring = newstring + string[ptr : len(string)]

        string = newstring

    elif supers:
        # An inline style that uses replacement with a different
        # character. Strings are immutable so we used a list instead
        # for the in-place changes. Convert that list back to a string
        # object.

        string = ""

        for ch in muttable_string:
            string += ch

    elif dont_decorate:
        # Do nothing and return string unchanged.

        pass

    else:
        # A separate line with pointers or dashes is used for highlighting.
        #
        # This style requires two lines of output:
        #   1. the string to be decorated which is unchanged;
        #   2. the string of decorations immediately underneath.

        string = string + "\n" + marker_string

    return string


def get_tuples(string, substring):
    list_of_tuples = []
    ptr = 0
    slice_length = len(substring)

    while ptr < len(string):
        if string[ptr : ptr + slice_length] == substring:
            list_of_tuples.append((ptr, slice_length))
            ptr += slice_length

        else:
            ptr += 1

    # The list of tuples returned may be empty
    return list_of_tuples


def is_valid_file(parser, arg):
    if not os.path.isfile(arg):
        parser.error("The file %s does not exist" % arg)

    else:
        # Return filename

        return arg


######################################################################
# Scan book for superfluous asterisks
######################################################################


def asterisk_check():
    print("asterisk check\n", file=log)

    # Regex for for a thought-break
    regex_tb = re.compile(r"\*       \*       \*       \*       \*$")

    # Regex for a random '*' in text
    regex_as = re.compile(r"\*")

    no_asterisks_found = True
    rec_cnt = 0
    line_number = 0  # it will be immediately incremented after first line read

    for line in book:
        line_number += 1

        # Ignore any thought-breaks in text
        # **DISABLED** so shows tb's as well

        # if regex_tb.search(line):
        #    continue

        if regex_as.search(line):
            # Found an unexpeceted asterisks

            no_asterisks_found = False

            if verbose or rec_cnt < 5:
                # Log record is all text so convert line number to a string
                ln = str(line_number)

                # Right justify line number in a 7-digit record field
                filler = 7 - len(ln)
                output_record = " " * filler
                output_record = output_record + ln + ": "

                # Append text of line
                output_record = output_record + line

                print(output_record, file=log)

                print(" ", file=log)

            rec_cnt += 1

    # Get here when all lines in the book have been scanned for unexpected asterisks

    if not verbose and rec_cnt > 5:
        # We've only output the first five lines so say how many more there are

        remaining = rec_cnt - 5
        print("    ...", remaining, "more\n", file=log)

    if no_asterisks_found:
        print(" no lines with unexpected asterisks found\n", file=log)

    template = "{}"
    print(template.format("-" * 80), file=log)


######################################################################
# Scan book for two or more adjacent spaces on a line that
# does not start with a space
######################################################################


def adjacent_spaces():
    print("adjacent spaces check\n", file=log)

    # Regex for for two adjacent spaces
    regex_adj = re.compile(r"\s\s+?")

    # Regex for for one or more spaces at start of a line
    regex_ld = re.compile(r"^\s+?")

    no_adjacent_spaces_found = True
    rec_cnt = 0
    line_number = 0  # it will be immediately incremented after first line read

    for line in book:
        line_number += 1

        # Lines that start with one or more spaces (poetry, block-quotes, etc.)
        # will fail the 'if' below

        if regex_adj.search(line) and not regex_ld.search(line):
            # Line with adjacent spaces AND no leading spaces

            no_adjacent_spaces_found = False

            if verbose or rec_cnt < 5:
                # Log record is all text so convert line number to a string
                ln = str(line_number)

                # Right justify line number in a 7-digit record field
                filler = 7 - len(ln)
                output_record = " " * filler
                output_record = output_record + ln + ": "

                # Append text of line
                output_record = output_record + line

                print(output_record, file=log)

                print(" ", file=log)

            rec_cnt += 1

    # Get here when all lines in the book have been scanned for adjacent spaces

    if not verbose and rec_cnt > 5:
        # Tell user how many, if any, lines above 5 contain adjacent spaces

        remaining = rec_cnt - 5
        print("    ...", remaining, "more\n", file=log)

    if no_adjacent_spaces_found:
        print(" no lines with adjacent spaces found\n`", file=log)

    template = "{}"
    print(template.format("-" * 80), file=log)


######################################################################
# Scan book for trailing spaces
######################################################################


def trailing_spaces():
    print("trailing spaces check\n", file=log)

    # Regex for a line with one trailing space at end
    regex_tsp = re.compile(r" $")

    no_trailing_spaces_found = True
    rec_cnt = 0
    line_number = 0  # it will be immediately incremented after first line read

    for line in book:
        line_number += 1

        if regex_tsp.search(line):
            # We've found a line with at least one trailing space

            no_trailing_spaces_found = False

            if verbose or rec_cnt < 5:
                # Log record is all text so convert line number to a string
                ln = str(line_number)

                # Right justify line number in a 7-digit record field
                filler = 7 - len(ln)
                output_record = " " * filler
                output_record = output_record + ln + ": "

                # Append text of line
                output_record = output_record + line

                print(output_record, file=log)

                print(" ", file=log)

            rec_cnt += 1

    # Get here when all lines in the book have been scanned for trailing spaces

    if not verbose and rec_cnt > 5:
        # Tell user how many, if any, lines above 5 contain trailing spaces

        remaining = rec_cnt - 5
        print("    ...", remaining, "more\n", file=log)

    if no_trailing_spaces_found:
        print(" no lines with trailing spaces found\n", file=log)

    template = "{}"
    print(template.format("-" * 80), file=log)


######################################################################
# Unusual character check. This will collect and output to the log
# file, lines that contain characters ('weirdos') not normally found
# in an English text. A caret underneath such characters highlights
# them in the log file.
######################################################################


def weird_characters():
    print("unusual characters check\n", file=log)

    no_weirdos = True

    # arrow = "↑"
    arrow = "^"

    # Regex for a line of containing only normal characters.
    regex_all_normal = re.compile(r"^[A-Za-z0-9\s.,:;?!\-_—–=“”‘’{}]+$")

    # Regex for the set of 'weird' characters. Note these are
    # all the characters NOT in the normal set above.
    regex_weird = re.compile(r"[^A-Za-z0-9\s.,:;?!\-_—–=“”‘’{}]")

    # Regex for an empty line or all whitespace
    regex_all_whitespace = re.compile(r"^ *$")

    line_number = 0  # it will be immediately incremented after first line read

    # Build up a dictionary. The keys are 'weird' characters and the values are a
    # list of one or more tuples. Each tuple contains a line number and the text of
    # that line which will contain one or more instances of that weird character.
    # The tuples in the list are in (increasing) line number order.
    #
    # The dictionary and its values is mapped directly to the layout in the log by
    # the code that follows.

    weird_dict = {}

    for line in book:
        line_number += 1
        marker_str = ""

        # Test for a line containing one or more 'weird' characters.

        if not regex_all_normal.search(line) and not regex_all_whitespace.search(line):
            # We get here if at least one weird character found in the line.

            no_weirdos = False

            # Create a tuple for the line because it contains AT LEAST ONE weirdo
            tple = (line_number, line)

            # Run along line and add a tuple for each weirdo found
            for ch in line:
                # Is character a weirdo?

                if regex_weird.match(ch):
                    # It is so update dictionary. This will mean either adding a tuple
                    # to the value (a list of tuples) of an existing dictionary key
                    # (a weirdo) or adding a new key and value to the dictionary

                    if ch in weird_dict:
                        # Append new tuple to list for this weirdo

                        weird_dict[ch].append(tple)

                    else:
                        # Add a new key/weirdo and its initial value to dictionary

                        weird_dict[ch] = []
                        weird_dict[ch].append(tple)

    # Have read all lines in book and built a dictionary of lines containing weirdos.
    # Process dictionary entries to produce output records for the log.

    for weirdo in weird_dict:
        # Get the list of tuples (line number, line text) for this weirdo. The line
        # text in each tuple will contain one or more instances of the weirdo.

        weirdo_lines_list = weird_dict[weirdo]

        # If a weirdo occurs more than once on a line, there will be a tuple in
        # the list for each occurrence. We only need one instance for that line
        # so remove the redundant tuples. Note we will later scan the text of each
        # record to be output to the log. A record will contain a line number and
        # the text of that line and we will highlight each appearance of the weirdo
        # in the record/line that is output.

        # Recall that a tuple is: (line number, line text)

        if len(weirdo_lines_list) > 1:
            cnt = 1

            for tple in weirdo_lines_list:
                if cnt == 1:
                    new_tuples_list = []
                    # There has to be at least one tuple in the list
                    new_tuples_list.append(tple)
                    prev_line_number = tple[0]

                else:
                    if tple[0] == prev_line_number:
                        # Redundant tuple so nothing to copy

                        continue

                    else:
                        # Have encountered a tuple with a new line number.
                        # Add it to the new tuples list

                        new_tuples_list.append(tple)
                        prev_line_number = tple[0]

                cnt += 1

            # List of tuples will now have all redundant tuples removed

            weirdo_lines_list = new_tuples_list

        # We get here with a new weirdo lines list of one or more tuples. Redundant
        # entries for a line have been removed. That is, the line numbers in each
        # tuple are different and are in increasing order of appearance in the book.

        # Use this list of tuples to produce records to be written to the log.

        # Output weirdo character on a line of its own

        weirdo_char = "'" + weirdo + "'"
        print(decorate(weirdo_char, [(1, 1)], "bold"), file=log)

        rec_cnt = 0

        for tple in weirdo_lines_list:
            if verbose or rec_cnt < 2:
                # Extract line number and line text from tuple.

                line_number = tple[0]  # int
                line_text = tple[1]  # string

                # Log record is all text so convert line number to a string
                ln = str(line_number)

                # Right justify line number in a 7-digit record field
                filler = 7 - len(ln)
                output_record = " " * filler
                output_record = output_record + ln + ": "

                # Append line text
                output_record = output_record + line_text

                # Record completed. Now scan record for each occurrence of the weirdo
                # and build a list of tuples. Each tuple represents a slice of the string
                # with the first value of the tuple being the position of the weirdo in
                # the string and the second value in the tuple being the length of the
                # slice. In this # case the length is 1; that is, single characters will
                # be highlighted.

                ptr = 0
                list_of_tuples = []

                for ch in output_record:
                    if ch == weirdo:
                        list_of_tuples.append((ptr, 1))
                    ptr += 1

                print(decorate(output_record, list_of_tuples, "red"), file=log)

            rec_cnt += 1

        # Processed all the tuples in the list for this weirdo

        print(" ", file=log)

        if not verbose and rec_cnt > 2:
            # Tell user how many, if any, lines above 2 remain

            remaining = len(weirdo_lines_list) - 2
            print("    ...", remaining, "more\n", file=log)

        # We are now done for this weirdo. There may be more weirdos in
        # dictionary to similarly process

    if no_weirdos:
        print(" no unusual characters found\n", file=log)

    template = "{}"
    print(template.format("-" * 80), file=log)


######################################################################
# blank line spacing check
######################################################################


def spacing_check():
    print("spacing check", file=log)
    print(
        "\nNB Any spacing until the first four-line space is ignored. Otherwise it expects",
        file=log,
    )
    print(
        "   4-1-2-1, 4-2-1 or 4-1-1 variations only. Exceptions to those spacing patterns",
        file=log,
    )
    print(
        "   are flagged as superscript. If you really need that spacing then ignore the",
        file=log,
    )
    print("   flags!\n", file=log)

    # This routine does not use the line text at all. It is only concerned with
    # counting blank lines between paragraphs and other lines of text/blocks.

    consec = 0  # consecutive blank lines

    line_number = 0  # it will be immediately incremented after first line read

    # The very first 'last paragraph start' line is one in GG, not 0
    last_line_number = 1

    # String of spacing counts
    s = ""

    # Record to be written to log. It's contructed from the line number that starts
    # the first text block of a sequence of blank-line delineated text blocks that
    # eventually end with exactly 4 blank lines. The string of counts of blank lines
    # found in the sequence is appended.
    # NB It also handles an input file in which no blocks of text end with exactly
    #    4 blank lines.
    output_record = ""

    # Regex for an empty line or all whitespace
    regex_spaces = re.compile(r"^ *$")

    # Regex for replacement of strings of three or more '1' by '1..1'
    regex_ones = re.compile(r"1111*")
    repl_ones = "1..1"

    # Regexes for counts/sequences of counts to replace with highlighted versions
    # NB The highlighting involves replacing the regex values with their superscript
    #    version. That is, same digits but as superscripts.
    regex_3 = re.compile(r"3")
    regex_5 = re.compile(r"5")
    regex_22 = re.compile(r"22")
    regex_44 = re.compile(r"44")
    repl_3 = "³"
    repl_5 = "⁵"
    repl_22 = "²²"
    repl_44 = "⁴⁴"

    for line in book:
        line_number += 1

        if regex_spaces.match(line):
            consec += 1
            continue

        # Here if non-blank line.
        #
        # If encountered after seeing four or more consecutive
        # blank lines, start a new string of spaces counts. this
        # handles the possibility there may be 5 blank lines, the
        # fifth being there in error. That count of 5 will be
        # specially flagged in the output.

        if consec >= 4:
            # Flush the current string of blank-line counts to output rec.

            # Before doing that, replace long sequences of '1' with '1..1'
            # and flag any 'invalid' counts of blank lines such as 3 or 5.

            list_of_tuples = []

            s = regex_ones.sub(repl_ones, s)

            L = get_tuples(s, "3")
            for tple in L:
                list_of_tuples.append(tple)
            L = get_tuples(s, "5")
            for tple in L:
                list_of_tuples.append(tple)
            L = get_tuples(s, "22")
            for tple in L:
                list_of_tuples.append(tple)
            L = get_tuples(s, "44")
            for tple in L:
                list_of_tuples.append(tple)

            s = decorate(s, list_of_tuples, "red")

            # s = regex_3.sub(repl_3, s)
            # s = regex_5.sub(repl_5, s)
            # s = regex_22.sub(repl_22, s)
            # s = regex_44.sub(repl_44, s)

            # Log record is all text so convert last line number to a string
            ln = str(last_line_number)

            # Right justify line number in a 7-digit record field
            filler = 7 - len(ln)
            output_record = " " * filler
            output_record = output_record + ln + ": " + s
            print(output_record, file=log)
            s = str(consec)
            last_line_number = line_number
        else:
            # Non-blank line and fewer than 4 consecutive blank lines counted

            if consec > 0:
                s = s + str(consec)

        # Non-blank line seen so restart consecutive blank-line count
        consec = 0

    # Print last line of buffered output

    list_of_tuples = []

    s = regex_ones.sub(repl_ones, s)

    s = regex_ones.sub(repl_ones, s)
    L = get_tuples(s, "3")
    for tple in L:
        list_of_tuples.append(tple)
    L = get_tuples(s, "5")
    for tple in L:
        list_of_tuples.append(tple)
    L = get_tuples(s, "22")
    for tple in L:
        list_of_tuples.append(tple)
    L = get_tuples(s, "44")
    for tple in L:
        list_of_tuples.append(tple)

    s = decorate(s, list_of_tuples, "red")

    # The record to be written to the log is all text so convert the
    # line number of the start of the last paragraph to a string.
    ln = str(last_line_number)

    # Right justify the line number in a record field that allows up to
    # seven digits.
    filler = 7 - len(ln)
    output_record = " " * filler
    output_record = output_record + ln + ": " + s
    print(output_record, file=log)

    template = "\n{}"
    print(template.format("-" * 80), file=log)


######################################################################
# short lines check
######################################################################


def short_lines_check():
    print("short lines check\n", file=log)

    # The below from Project Gutenberg via Roger Franks:

    SHORTEST_PG_LINE = 55
    LONGEST_PG_LINE = 75
    FAR_TOO_LONG = 80

    # Short line definition:
    #   No leading space but some text (ANY characters)
    #   <= 55 characters long
    #   Following line has some non-space text (ANY characters)

    # METHOD
    # Slide a 2-line window through the lines of text, moving window forward
    # one line at a time. Deal specially with the first two lines of book.
    # Look for short line as first line in window then advance window.

    # Contains at least one non-space character
    regex_ns = re.compile("\S+?")

    # Contains leading space
    regex_ld = re.compile("^\s+?")

    no_short_lines = True

    line_number = 0  # it will be immediately incremented after first line read

    book_length = len(book)  # How many lines there are in book

    if book_length <= 2:
        print(" short book - only 1 or 2 lines long!\n", file=log)

        template = "{}"
        print(template.format("-" * 80), file=log)

        return

    # Here if book is at least 3 lines long

    # Set up window - loop will skip first line of book (book[0])
    window_line_2 = book[0]

    rec_cnt = 0

    for line in book:
        line_number += 1

        # Skip the first line of the book - see comment below
        if line_number == 1:
            continue

        # Slide window one line forward. Note special case of the first window,
        # that is when line_number == 2. At this point window_line_2 contains
        # the first line of the book.

        window_line_1 = window_line_2
        window_line_2 = line

        # In the 3 tests below, the 'if' logic is the inverse (NOT) of the criteria.
        # This means that if any test fails then we can stop further testing in this
        # window and slide it forward one line and repeat the tests.

        # Test 3 criteria: line 2 has some non-space characters.
        if not regex_ns.search(line):
            continue

        # Test 2 criteria: line 1 has no leading spaces but some non-space characters.
        if regex_ld.search(window_line_1) or not regex_ns.search(window_line_1):
            continue

        # Test 1 criteria: line <= 55 long.
        if len(window_line_1) > 55:
            continue

        # We get here only if all criteria for a short line are met.

        no_short_lines = False

        if verbose or rec_cnt < 5:
            # Write the two lines in the window to the log. Flag the short one (line 1)

            # Log record is all text so convert line numbers to a string
            ln1 = str(line_number - 1)
            ln2 = str(line_number)

            # Right justify line number of short line (line 1) in a 7-digit record field

            filler = 7 - len(ln1)
            output_record = " " * filler
            output_record = output_record + ln1 + ": " + window_line_1

            # Now append flag (' *SHORT*') at position 64 in output record string

            if len(output_record) > 64:
                # It shouldn't be!
                #   Line number (7)
                #   ': '        (2)
                #   text of line (<= 55 characters)
                # = 64 characters maximum

                print(
                    "DEBUG Big problem in River City:",
                    len(output_record),
                    output_record,
                    file=log,
                )
                print(" ", file=log)

                break

            else:
                # len(output_record) <= 64 as should be the case.

                # Pad end of record to a line length of 72 characters
                # so that slicing first part of the record doesn't take
                # us past right-bound of the string.

                while len(output_record) < 72:
                    output_record = output_record + " "

                # Slice off the first 64 characters then add the flag to the slice

                output_record = output_record[0:63] + " *SHORT*"

                print(output_record, file=log)

            # Now do line 2 (which isn't flagged but is output as its presence can
            # determine whether the previous line is 'short'.

            # Right justify line number in a 7-digit record field
            filler = 7 - len(ln2)
            output_record = " " * filler
            output_record = output_record + ln2 + ": " + window_line_2

            print(output_record, file=log)

            print(" ", file=log)

        # Continue counting short lines found
        rec_cnt += 1

    # We have finished sliding the window over the book.

    if not verbose and rec_cnt > 5:
        # Tell user how many, if any, lines above 5 contain short lines

        remaining = rec_cnt - 5
        print("    ...", remaining, "more\n", file=log)

    if no_short_lines:
        print(
            " no lines less than 55 characters long meet 'short line' criteria\n",
            file=log,
        )

    template = "{}"
    print(template.format("-" * 80), file=log)


######################################################################
# long lines check
######################################################################


def long_lines_check():
    print("long lines check\n", file=log)

    line_number = 0  # it will be immediately incremented after first line read

    long_line_list = []

    no_long_lines = True

    for line in book:
        line_number += 1

        line_length = len(line)
        if line_length > 72:
            # Add tuple to a list of long lines, Each tuple is (line number, line length, line text)
            long_line_list.append((line_number, line_length, line))
            no_long_lines = False

    # All lines in book measured and list of long-line tuples built

    # Sort list of tuples into order of decreasing line length using as the key the
    # line length specified in each tuple

    long_line_list = sorted(long_line_list, key=lambda text: text[1], reverse=True)

    # Write contents of long lines list to log

    rec_cnt = 0

    for tple in long_line_list:
        if verbose or rec_cnt < 5:
            # Extract line number, line length and line text from tuple.

            ln = str(tple[0])  # (int) line number
            ll = str(tple[1])  # (int) line length
            lt = tple[2]  # (str) line text

            # NB Log record is all text

            # Right justify line number in a 7-digit record field
            filler = 7 - len(ln)
            output_record = " " * filler
            output_record = output_record + ln + ": "

            # Append line length and line text
            output_record = output_record + "(" + ll + ") " + lt + "\n"

            print(output_record, file=log)

        # Continue counting long lines
        rec_cnt += 1

    # We've finished working through the list of long lines

    if not verbose and rec_cnt > 5:
        # We've only output the first five long lines so say how many more there are

        remaining = rec_cnt - 5
        print("    ...", remaining, "more\n", file=log)

    if no_long_lines:
        print(" no long lines found in text\n", file=log)

    template = "{}"
    print(template.format("-" * 80), file=log)


######################################################################
# repeated words check
######################################################################


def repeated_words_check():
    print("repeated words check\n", file=log)

    ###########################################################
    # NB
    # re.findall() and re.finditer() cannot be used to find all
    # the pairs of repeated words in a paragraph as they search
    # for non-overlapping pairs with the regex defined below.
    # That means you could miss some pairs of repeated words in
    # the paragraph.
    ###########################################################

    # Regex to find double words. A word is defined below as
    # consisting of two or more regular expression 'word'
    # characters. It matches two words separated by one or
    # more spaces. Each word is captured by a separate group
    # subpattern and that grouping is exploited in the logic
    # below.

    regex_dw = re.compile(r"(\b\w\w+?\b)\s+?(\b\w\w+?\b)")

    no_repeated_words = True

    for para in paras:
        # Are there any 'pairs of words' in this paragraph? That is, two words
        # separated by whitespace. It might, for example, just contain the string
        # 'Chapter I' and nothing else. That is not a 'pair of words' for the
        # purposes of the repeated word check and will not be matched by the
        # regex. Note that 'Chapter II' would be, however.
        #
        # The search commences at the start of the paragraph. If it finds a
        # pair of words, it checks if they are both the same and processes as
        # appropriate. It then recommences the search of the paragraph for
        # more pairs at the second word of the pair previously matched. In that
        # sense it is doing overlapping matches of pairs of words and thus avoids
        # the limitations of re.findall(), etc., when using the regex defined above.

        # Start at beginning of the paragraph. After first pair of words matched
        # start_at will point to the first letter of the second word of that pair
        # and so on.

        start_at = 0

        res = regex_dw.search(para[start_at:])

        if not res:
            # No pairs of words found in this paragraph so skip to next one.

            continue

        # Here when at least one pair of words found in a paragraph.

        while res:
            # We have a pointer to a pair of words separated by whitespace.

            # Are the two words the same?

            if res.group(1) == res.group(2):
                # Yes, they are repeated words.

                no_repeated_words = False

                # We want to output the repeated words roughly in the
                # middle of a line with as many words at both ends that
                # that can fit into a width of 30 characters. If the
                # repeated words appear near the start or end of a
                # paragraph then they cannot be centred on the line
                # that is output to the log.

                # The variable 'indx' is the position of the first letter
                # of the pair of words just identified in the 'para'
                # string.

                indx = para.index(res.group(0))

                llim = indx - 30
                rlim = indx + 30

                if llim < 0:
                    llim = 0
                    rlim = 60

                if rlim > len(para):
                    llim = len(para) - 60
                    rlim = len(para)

                if llim <= 0:
                    llim = 0

                # As a result of the abitrary width limits chosen above, the start and
                # end of string to be output to the log may have partial words. Expand
                # string at both ends until first whitespace character found or start
                # or end of paragraph encountered. String will now have only complete
                # words.

                while llim > 0 and para[llim : llim + 1] != " ":
                    llim -= 1

                while rlim < len(para) and para[rlim : rlim + 1] != " ":
                    rlim += 1

                # Now at this point the string containing the repeated
                # words may have been expanded at both ends so the original
                # starting index of the first repeated word cannot be used.
                # Locate the repeated words in this new string. They should
                # be there!

                slice_start = para[llim:rlim].index(res.group(0))
                slice_length = len(res.group(0))

                # Output the decorated staring.

                print(
                    decorate(para[llim:rlim], [(slice_start, slice_length)], "red"),
                    file=log,
                )
                print(" ", file=log)

            # end-if

            # Continue searching paragraph for more word pairs. Search will
            # recommence from the second word of the pair we just looked at.

            start_at += res.start(2)
            res = regex_dw.search(para[start_at:])

        # end-while

    # end-for

    # Here when no more paras to search

    if no_repeated_words:
        print(" no repeated words found in text\n", file=log)

    template = "{}"
    print(template.format("-" * 80), file=log)


######################################################################
# ellipses check
######################################################################


def ellipses_check():
    print("ellipses check\n", file=log)

    # It checks for:
    #
    #    3-dot ellipses without a space before them
    #    3-dot ellipses followed by full-stop and no trailing space
    #      (AKA 4-dot ellipses)
    #    2-dot ellipses
    #    5-or-more-dot ellipses
    #
    # and outputs any lines (and their line numbers) that have them.

    # The comments and code below are a direct implementation in Python
    # of code written in Go by Roger Franks (rfranks).

    # give... us some pudding, give...us some pudding
    re1 = re.compile(r"\w\.\.\.[\s\w]")

    # give....us some pudding
    re2 = re.compile(r"\w\.\.\.\.\w")

    # give.. us pudding, give ..us pudding, give .. us pudding
    re3 = re.compile(r"[\s\w]\.\.[\s\w]")

    # give .....us some pudding, // give..... us some pudding, // give ..... us some pudding
    re4 = re.compile(r"[\s\w]\.\.\.\.\.*[\s\w]")

    # ... us some pudding (start of line)
    re5 = re.compile(r"^\.")

    # give ... (end of line)
    re6 = re.compile(r"[^\.]\.\.\.$")

    # found in the wild according to Roger. Picked up by re6 above.
    # re7 := regexp.MustCompile(`\.\s\.+`) // but the cars. ...

    re8 = re.compile(r"(^|[^\.])\.\.($|[^\.])")  # was becoming διαστειχων..

    # Do explicit check for give us some pudding ....
    re9 = re.compile(r"\s\.\.\.\.$")

    no_ellipses_found = True
    rec_cnt = 0
    line_number = 0  # it will be immediately incremented after first line read

    for line in book:
        line_number += 1

        if (
            re1.search(line)
            or re2.search(line)
            or re3.search(line)
            or re4.search(line)
            or re5.search(line)
            or re6.search(line)
            or re8.search(line)
            or re9.search(line)
        ):
            # Found a bad 'un

            if verbose or rec_cnt < 5:
                no_ellipses_found = False

                # Log record is all text so convert line number to a string
                ln = str(line_number)

                # Right justify line number in a 7-digit record field
                filler = 7 - len(ln)
                output_record = " " * filler
                output_record = output_record + ln + ": "

                # Append text of line
                output_record = output_record + line

                print(output_record, file=log)

                print(" ", file=log)

            rec_cnt += 1

    # Here when all lines in book read and checked

    if not verbose and rec_cnt > 5:
        # We've only output the first five lines so say how many more there are

        remaining = rec_cnt - 5
        print("    ...", remaining, "more\n", file=log)

    if no_ellipses_found:
        print(" no incorrect ellipse usage found in text\n", file=log)

    template = "{}"
    print(template.format("-" * 80), file=log)


######################################################################
# abandoned HTML tag check
######################################################################


def html_check():
    print("abandoned HTML tag check\n", file=log)

    no_tags_found = True
    rec_cnt = 0

    regex_tg = re.compile(r"<\/*?.*?>")

    line_number = 0  # it will be immediately incremented after first line read

    for line in book:
        line_number += 1

        if regex_tg.search(line):
            # Looks like it contains an HTML tag

            if verbose or rec_cnt < 5:
                no_tags_found = False

                # Log record is all text so convert line number to a string
                ln = str(line_number)

                # Right justify line number in a 7-digit record field
                filler = 7 - len(ln)
                output_record = " " * filler
                output_record = output_record + ln + ": "

                # Append text of line
                output_record = output_record + line

                print(output_record, file=log)

                print(" ", file=log)

            rec_cnt += 1

    # Get here when all lines in the book have been scanned for abandoned HTML tags

    if not verbose and rec_cnt > 5:
        # We've only output the first five lines so say how many more there are

        remaining = rec_cnt - 5
        print("    ...", remaining, "more\n", file=log)

    if no_tags_found:
        print(" no abandoned HTML tags found in text\n", file=log)

    template = "{}"
    print(template.format("-" * 80), file=log)


######################################################################
# dash review
######################################################################


def dash_review():
    print("hyphen/dashes check\n", file=log)

    no_suspect_dashes_found = True
    rec_cnt = 0

    # Looks like I forgot a double-hyphens -here and here-
    re1 = re.compile(r"[^\-]-[\s$]")


#########################################
#
# MAIN PROGRAM
#
#########################################

if platform.system() == "Windows":
    os.system("color")

book = []
paras = []

# Usage and command line arguments

parser = argparse.ArgumentParser()
parser.add_argument(
    "INPUT", type=lambda x: is_valid_file(parser, x), help="input text file"
)
parser.add_argument(
    "-o",
    "--output",
    help="output log file",
    type=argparse.FileType("w", encoding="UTF-8"),
)
parser.add_argument(
    "-d", "--debug", help="write debug info to output log file", action="store_true"
)
parser.add_argument("-v", "--verbose", help="verbose output", action="store_true")
args = parser.parse_args()

# Positional argument - input text
srcfile = args.INPUT

# Default log output
log = sys.stdout
sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

# Redirect log output if optional output file specified

if args.output:
    logfile = args.output.name
    log = open(logfile, "w", encoding="utf-8")

# Debug is an optional argument

debug = False
if args.debug:
    debug = True
if debug:
    print("Debugging...")

verbose = False
if args.verbose:
    verbose = True

# Do we still have input and output files connected?

if not os.path.isfile(srcfile):
    print("No source file: ", srcfile, sep="")
    exit()

if not log:
    print("No output file (or stdout) assigned")
    exit()

# Read book a line at a time into list book[]

input = open(srcfile, "r", encoding="utf-8")
for line in input:
    line = line.rstrip("\n")
    line = line.rstrip("\r")
    book.append(line)
input.close()

# Read book again, this time a paragraph at a time

# The input is buffered and only appended to the 'paras' string
# when either a blank line is encountered or end of input file.

# Ignore leading blank lines in file
ignore = True

input = open(srcfile, "r", encoding="utf-8")
for line in input:
    line = line.rstrip("\n")
    line = line.rstrip("\r")

    if len(line) == 0 and ignore:
        # A leading blank line to be ignored

        continue

    if len(line) != 0 and ignore:
        # First non-empty line in file

        ignore = False
        buffer = ""
        new_buffer = True

    if len(line) == 0:
        # End of paragraph

        if len(buffer) > 0:
            paras.append(buffer)
            buffer = ""
            new_buffer = True

            # Get next line from book

            continue

    else:
        if not new_buffer:
            # As buffer is not empty need to prefix lines with a separator

            line = " " + line

        else:
            # Buffer should be empty. First line being appended needs no separator

            pass

    # Append line to buffer
    buffer = buffer + line
    new_buffer = False

# End of book. If anything in the buffer add it to string

if len(buffer) > 0:
    paras.append(buffer)

input.close()

###################################################
# We're done reading the input. Start processing it.
###################################################

print(decorate("RED", [(0, 3)], "red"))
print(decorate("GREEN", [(0, 5)], "green"))
print(decorate("YELLOW", [(0, 6)], "yellow"))
print(decorate("BOLD", [(0, 4)], "bold"))
print(decorate("ITALIC", [(0, 6)], "italic"))
print(decorate("UNDERLINE", [(0, 9)], "underline"))

# The checks are run in the following order...

asterisk_check()
adjacent_spaces()
trailing_spaces()
weird_characters()
spacing_check()
short_lines_check()
long_lines_check()
repeated_words_check()
ellipses_check()
html_check()
