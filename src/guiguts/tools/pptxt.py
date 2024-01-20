"""PPtxt checking tool.

Can be run as a standalone tool, or called from within Guiguts.
Requires regex module to be installed."""

import argparse
import sys
import os
import io
import platform
import regex as re

########################################################
# pptxt.py
# Perl author: Roger Franks (DP:rfrank) - 2009
# Go author: Roger Franks (DP:rfrank) - 2020
# Python author: Quentin Campbell (DP:qgc) - 2024
# Last edit: 15-jan-2024
########################################################


class color:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    REDONYELLOW = "\033[31;43m"
    BOLD = "\033[1m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def is_valid_file(parser, arg):
    if not os.path.isfile(arg):
        parser.error("The file %s does not exist" % arg)

    else:
        # Return filename
        return arg


def pptxt(string_in, string_out, verbose, highlight):
    def decorate(string, list_of_tuples, style):
        class super:
            TWO = "²"
            THREE = "³"
            FOUR = "⁴"
            FIVE = "⁵"

        # By default PPTXT no longer decorates/highlights certain
        # items in the report it outputs. If you want decoration
        # then enable it with the -d/--decorate argument at run time.

        if not highlight:
            # Just return string unchanged; i.e. without any highlighting.
            return string

        # Don't assume the tuples in the passed in list are sorted.
        # Make sure as they need to be for the sanity checks below.

        list_of_slices = list_of_tuples.copy()
        list_of_slices.sort()

        # There should be one or more tuples (slice_start, slice_length)
        # in list. Each tuple defines a slice of 'string' to be decorated.
        # If list is empty just returm original string.

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
                # See comments for 'red' style above.

                inline = True

                if slice_start == 0:
                    newstring = (
                        color.GREEN
                        + string[slice_start : slice_start + slice_length]
                        + color.END
                    )
                    ptr = slice_start + slice_length

                else:
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
                # See comments for 'red' style above.

                inline = True

                if slice_start == 0:
                    newstring = (
                        color.YELLOW
                        + string[slice_start : slice_start + slice_length]
                        + color.END
                    )
                    ptr = slice_start + slice_length

                else:
                    newstring = newstring + string[ptr:slice_start]
                    ptr = slice_start
                    newstring = (
                        newstring
                        + color.YELLOW
                        + string[slice_start : slice_start + slice_length]
                        + color.END
                    )
                    ptr = slice_start + slice_length

            elif style == "redonyellow":
                # See comments for 'red' style above.

                # Red characters on a yellow background.

                inline = True

                if slice_start == 0:
                    newstring = (
                        color.REDONYELLOW
                        + string[slice_start : slice_start + slice_length]
                        + color.END
                    )
                    ptr = slice_start + slice_length

                else:
                    newstring = newstring + string[ptr:slice_start]
                    ptr = slice_start
                    newstring = (
                        newstring
                        + color.REDONYELLOW
                        + string[slice_start : slice_start + slice_length]
                        + color.END
                    )
                    ptr = slice_start + slice_length

            elif style == "bold":
                # See comments for 'red' style above.

                inline = True

                if slice_start == 0:
                    newstring = (
                        color.BOLD
                        + string[slice_start : slice_start + slice_length]
                        + color.END
                    )
                    ptr = slice_start + slice_length

                else:
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
                # See comments for 'red' style above.

                inline = True

                if slice_start == 0:
                    newstring = (
                        color.ITALIC
                        + string[slice_start : slice_start + slice_length]
                        + color.END
                    )
                    ptr = slice_start + slice_length

                else:
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
                # See comments for 'red' style above.

                inline = True

                if slice_start == 0:
                    newstring = (
                        color.UNDERLINE
                        + string[slice_start : slice_start + slice_length]
                        + color.END
                    )
                    ptr = slice_start + slice_length

                else:
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
                # Return the string unchanged as no decoration specified. Use
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

    def make_a_report_record(line_number, line, wrap=True):
        # Return a record ready for printing to the report.
        # The default is to wrap the input line so that no
        # section exceeds 70 characters.

        if wrap:
            # Wrap the text in the argument 'line' into
            # a string with embedded newlines and a leader
            # of 9 spaces for all rewrapped sections after
            # the first. That aligns those sections with
            # the first which is prefixed with a 7-digit
            # right-aligned line number that is followed
            # by ": ".

            line = wrap_text9(line)

        template = "{: >7}: {}"

        return template.format(line_number, line)

    def get_centered_slice_endpoints(indx, para):
        # Define the start and end positions of a slice of the
        # 'para' string such that the position denoted by
        # 'indx' is roughly the center of the slice. The slice
        # will have as many whole words that can fit into about
        # 30 characters either side of 'indx'. If 'indx' is
        # near the start or end of the paragraph then the slice
        # cannot be centered around that position.

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

        # As a result of the abitrary width limits chosen above, the start
        # and end of the slice of the 'paragrpah' string defined by llim and
        # rlim may have partial words. Expand the slice at both ends until first
        # whitespace character found or start or end of paragraph encountered.
        # The slice that is defined will now have only complete words.

        while llim > 0 and para[llim : llim + 1] != " ":
            llim -= 1

        while rlim < len(para) and para[rlim : rlim + 1] != " ":
            rlim += 1

        return llim, rlim

    def wrap_text9(line):
        # Wrap the text in 'line' into a string with embedded newlines
        # and a leader of 9 spaces for all lines after the first.

        line2 = ""
        ch_cnt = 0
        line_length = len(line)

        for ch in line:
            ch_cnt += 1
            if ch_cnt >= 70 and ch_cnt < line_length - 8 and ch == " ":
                line2 += "\n         "
                ch_cnt = 0
            else:
                line2 += ch

        return line2

    ######################################################################
    # Scan book for superfluous asterisks
    ######################################################################

    def asterisk_check():
        print("asterisk check\n", file=string_out)

        # Regex for for a thought-break
        re_tb = re.compile(r"\*       \*       \*       \*       \*$")

        # Regex for a random '*' in text
        re_as = re.compile(r"\*")

        no_asterisks_found = True

        rec_cnt = 0
        line_number = 1
        for line in book:
            # Ignore any thought-breaks in text
            # **DISABLED** so shows tb's as well

            # if re_tb.search(line):
            #    line_number += 1
            #    continue

            if re_as.search(line):
                # Found an unexpeceted asterisks

                no_asterisks_found = False

                if verbose or rec_cnt < 5:
                    print(make_a_report_record(line_number, line), file=string_out)

                rec_cnt += 1

            line_number += 1

        # Get here when all lines in the book have been scanned for unexpected asterisks

        if not verbose and rec_cnt > 5:
            # We've only output the first five lines so say how many more there are

            remaining = rec_cnt - 5
            print("    ...", remaining, "more", file=string_out)

        if no_asterisks_found:
            print("    no lines with unexpected asterisks found\n", file=string_out)
        else:
            print(" ", file=string_out)

        template = "{}"
        print(template.format("-" * 80), file=string_out)

    ######################################################################
    # Scan book for two or more adjacent spaces on a line that
    # does not start with a space
    ######################################################################

    def adjacent_spaces():
        print("adjacent spaces check\n", file=string_out)

        # Regex for for two adjacent spaces
        re_adj = re.compile(r"\s\s+?")

        # Regex for for one or more spaces at start of a line
        re_ld = re.compile(r"^\s+?")

        no_adjacent_spaces_found = True

        rec_cnt = 0
        line_number = 1
        for line in book:
            # Lines that start with one or more spaces (poetry, block-quotes, etc.)
            # will fail the 'if' below

            if re_adj.search(line) and not re_ld.search(line):
                # Line with adjacent spaces AND no leading spaces

                no_adjacent_spaces_found = False

                if verbose or rec_cnt < 5:
                    print(make_a_report_record(line_number, line), file=string_out)

                rec_cnt += 1

            line_number += 1

        # Get here when all lines in the book have been scanned for adjacent spaces

        if not verbose and rec_cnt > 5:
            # Tell user how many, if any, lines above 5 contain adjacent spaces

            remaining = rec_cnt - 5
            print("    ...", remaining, "more", file=string_out)

        if no_adjacent_spaces_found:
            print("    no lines with adjacent spaces found\n`", file=string_out)
        else:
            print(" ", file=string_out)

        template = "{}"
        print(template.format("-" * 80), file=string_out)

    ######################################################################
    # Scan book for trailing spaces
    ######################################################################

    def trailing_spaces():
        print("trailing spaces check\n", file=string_out)

        # Regex for a line with one trailing space at end
        re_tsp = re.compile(r" $")

        no_trailing_spaces_found = True

        rec_cnt = 0
        line_number = 1
        for line in book:
            if re_tsp.search(line):
                # We've found a line with at least one trailing space

                no_trailing_spaces_found = False

                if verbose or rec_cnt < 5:
                    print(make_a_report_record(line_number, line), file=string_out)

                rec_cnt += 1

            line_number += 1

        # Get here when all lines in the book have been scanned for trailing spaces

        if not verbose and rec_cnt > 5:
            # Tell user how many, if any, lines above 5 contain trailing spaces

            remaining = rec_cnt - 5
            print("    ...", remaining, "more", file=string_out)

        if no_trailing_spaces_found:
            print("    no lines with trailing spaces found\n", file=string_out)
        else:
            print(" ", file=string_out)

        template = "{}"
        print(template.format("-" * 80), file=string_out)

    ######################################################################
    # Unusual character check. This will collect and output to the log
    # file, lines that contain characters ('weirdos') not normally found
    # in an English text. A caret underneath such characters highlights
    # them in the log file.
    ######################################################################

    def weird_characters():
        print("unusual characters check", file=string_out)

        no_weirdos = True

        # arrow = "↑"
        arrow = "^"

        # Regex for a line of containing only normal characters.
        re_all_normal = re.compile(r"^[A-Za-z0-9\s.,:;?!\-_—–=“”‘’{}]+$")

        # Regex for the set of 'weird' characters. Note these are
        # all the characters NOT in the normal set above.
        re_weird = re.compile(r"[^A-Za-z0-9\s.,:;?!\-_—–=“”‘’{}]")

        # Regex for an empty line or all whitespace
        re_all_whitespace = re.compile(r"^ *$")

        line_number = 1

        # Build up a dictionary. The keys are 'weird' characters and the values are a
        # list of one or more tuples. Each tuple contains a line number and the text of
        # that line which will contain one or more instances of that weird character.
        # The tuples in the list are in (increasing) line number order.
        #
        # The dictionary and its values is mapped directly to the layout in the log by
        # the code that follows.

        weird_dict = {}

        for line in book:
            marker_str = ""

            # Test for a line containing one or more 'weird' characters.

            if not re_all_normal.search(line) and not re_all_whitespace.search(line):
                # We get here if at least one weird character found in the line.

                no_weirdos = False

                # Create a tuple for the line because it contains AT LEAST ONE weirdo
                tple = (line_number, line)

                # Run along line and add a tuple for each weirdo found
                for ch in line:
                    # Is character a weirdo?

                    if re_weird.match(ch):
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
            line_number += 1

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
            print("\n", decorate(weirdo_char, [(1, 1)], "bold"), file=string_out)

            rec_cnt = 0

            for tple in weirdo_lines_list:
                if verbose or rec_cnt < 2:
                    # Extract line number and line text from tuple.

                    line_number = tple[0]  # int
                    line_text = tple[1]  # string

                    output_record = make_a_report_record(line_number, line_text)

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

                    print(
                        decorate(output_record, list_of_tuples, "red"), file=string_out
                    )

                rec_cnt += 1

            # Processed all the tuples in the list for this weirdo

            if not verbose and rec_cnt > 2:
                # Tell user how many, if any, lines above 2 remain

                remaining = len(weirdo_lines_list) - 2
                print("    ...", remaining, "more", file=string_out)

            # We are now done for this weirdo. There may be more weirdos in
            # dictionary to similarly process

        if no_weirdos:
            print("    \nno unusual characters found\n", file=string_out)
        else:
            print(" ", file=string_out)

        template = "{}"
        print(template.format("-" * 80), file=string_out)

    ######################################################################
    # blank line spacing check
    ######################################################################

    def spacing_check():
        print("spacing check", file=string_out)

        comment = "\nNB Any spacing until the first four-line space is ignored. From there, DP expects\n"
        comment += "   4121, 421 or 411 variations only. Exceptions to those spacing patterns will be\n"
        comment += "   highlighted by superscripting the line spacing counts; e.g. 41²²1. If you really\n"
        comment += "   need that unusual spacing then ignore the warnings.\n"
        print(comment, file=string_out)

        # This routine does not use the line text at all. It is only concerned with
        # counting blank lines between paragraphs and other lines of text/blocks.

        consec = 0  # consecutive blank lines

        line_number = 1

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
        re_spaces = re.compile(r"^ *$")

        # Regex for replacement of strings of three or more '1' by '1..1'
        re_ones = re.compile(r"1111*")
        repl_ones = "1..1"

        # Regexes for counts/sequences of counts to replace with highlighted versions.
        # NB The highlighting involves replacing the values in the regex with their
        #    superscript version. That is, same digits but as superscripts.
        re_3 = re.compile(r"3")
        re_5 = re.compile(r"5")
        re_22 = re.compile(r"22")
        re_44 = re.compile(r"44")
        repl_3 = "³"
        repl_5 = "⁵"
        repl_22 = "²²"
        repl_44 = "⁴⁴"

        for line in book:
            # Ignore blank lines.
            if re_spaces.match(line):
                consec += 1
                line_number += 1
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

                s = re_ones.sub(repl_ones, s)

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

                # s = decorate(s, list_of_tuples, "redonyellow")

                s = re_3.sub(repl_3, s)
                s = re_5.sub(repl_5, s)
                s = re_22.sub(repl_22, s)
                s = re_44.sub(repl_44, s)

                print(make_a_report_record(last_line_number, s), file=string_out)

                s = str(consec)
                last_line_number = line_number

            else:
                # Non-blank line and fewer than 4 consecutive blank lines counted

                if consec > 0:
                    s = s + str(consec)

            # Non-blank line seen so restart consecutive blank-line count
            consec = 0
            line_number += 1

        # Print last line of buffered output if its not empty.

        if len(s) != 0:
            # Find and highlight any anomalous spacing counts.
            list_of_tuples = []
            # First look for sequences of '1's and replace as appropriate.
            s = re_ones.sub(repl_ones, s)
            # Next find any '3' counts of blank lines.
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

            # s = decorate(s, list_of_tuples, "redonyellow")

            s = re_3.sub(repl_3, s)
            s = re_5.sub(repl_5, s)
            s = re_22.sub(repl_22, s)
            s = re_44.sub(repl_44, s)

            print(make_a_report_record(last_line_number, s), file=string_out)

        else:
            # Here if no four-line spacing found in book. Report that.

            print(
                "    no four-line spacing found in book - that's unusual!",
                file=string_out,
            )

        template = "\n{}"
        print(template.format("-" * 80), file=string_out)

    ######################################################################
    # short lines check
    ######################################################################

    def short_lines_check():
        print("short lines check\n", file=string_out)

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
        re_ns = re.compile(r"\S+?")

        # Contains leading space
        re_ld = re.compile(r"^\s+?")

        no_short_lines = True

        book_length = len(book)  # How many lines there are in book

        if book_length <= 2:
            print("    short book - only 1 or 2 lines long!\n", file=string_out)

            template = "{}"
            print(template.format("-" * 80), file=string_out)

            return

        # Here if book is at least 3 lines long

        # Set up window - loop will skip first line of book (book[0])
        window_line_2 = book[0]

        rec_cnt = 0
        line_number = 1
        for line in book:
            # Skip the first line of the book - see comment below
            if line_number == 1:
                line_number += 1
                continue

            # Slide window one line forward. Note special case of the first window;
            # that is, when line_number == 2. At this point window_line_2 contains
            # the first line of the book.

            window_line_1 = window_line_2
            window_line_2 = line

            # In the 3 tests below, the 'if' logic is the inverse (NOT) of the criteria.
            # This means that if any test fails then we can stop further testing in this
            # window and slide it forward one line and repeat the tests.

            # Test 3 criteria: line 2 has some non-space characters.
            if not re_ns.search(window_line_2):
                line_number += 1
                continue

            # Test 2 criteria: line 1 has no leading spaces but some non-space characters.
            if re_ld.search(window_line_1) or not re_ns.search(window_line_1):
                line_number += 1
                continue

            # Test 1 criteria: line <= 55 long.
            if len(window_line_1) > 55:
                line_number += 1
                continue

            # We get here only if all criteria for a short line are met.

            no_short_lines = False

            if verbose or rec_cnt < 5:
                # Write the two lines in the window to the log. Flag the short one (line 1)

                # Log record is all text so convert line numbers to a string
                ln1 = str(line_number - 1)
                ln2 = str(line_number)

                window_line_1 = decorate(
                    window_line_1, [(0, len(window_line_1))], "yellow"
                )
                print(make_a_report_record(ln1, window_line_1), file=string_out)
                # output_record = make_a_report_record(ln1, window_line_1)

                # Now do line 2 (which isn't highlighted) but is output as context;
                # its presence can determine whether the previous line is 'short'.

                print(make_a_report_record(ln2, window_line_2), file=string_out)

                print(" ", file=string_out)

            # Continue counting short lines found
            rec_cnt += 1
            line_number += 1

        # We have finished sliding the window over the book.

        if not verbose and rec_cnt > 5:
            # Tell user how many, if any, lines above 5 contain short lines

            remaining = rec_cnt - 5
            print("    ...", remaining, "more\n", file=string_out)

        if no_short_lines:
            print(
                "    no lines less than 55 characters long meet 'short line' criteria\n",
                file=string_out,
            )

        template = "{}"
        print(template.format("-" * 80), file=string_out)

    ######################################################################
    # long lines check
    ######################################################################

    def long_lines_check():
        print("long lines check\n", file=string_out)

        long_line_list = []
        no_long_lines = True

        line_number = 1
        for line in book:
            line_length = len(line)
            if line_length > 72:
                # Add tuple to a list of long lines, Each tuple is (line number, line length, line text)
                long_line_list.append((line_number, line_length, line))
                no_long_lines = False

            line_number += 1

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

                # Just create the line number part of the record by giving
                # function a zero-length line of text. We'll add the line
                # text and the prefixing line length next.

                output_record = make_a_report_record(ln, "")

                # Append line length and line text
                output_record = output_record + "(" + ll + ") " + lt

                print(output_record, file=string_out)

            # Continue counting long lines
            rec_cnt += 1

        # We've finished working through the list of long lines

        if not verbose and rec_cnt > 5:
            # We've only output the first five long lines so say how many more there are

            remaining = rec_cnt - 5
            print("    ...", remaining, "more", file=string_out)

        if no_long_lines:
            print("    no long lines found in text\n", file=string_out)
        else:
            print(" ", file=string_out)

        template = "{}"
        print(template.format("-" * 80), file=string_out)

    ######################################################################
    # repeated words check
    ######################################################################

    def repeated_words_check():
        print("repeated words check\n", file=string_out)

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
        # more spaces. That means 'Chapter II' would match but
        # 'Chapter I' would not (second 'word' not two characters).
        #
        # Each word is captured by a separate group subpattern and
        # that grouping is exploited in the logic below.

        re_dw = re.compile(r"(\b\w\w+?\b)\s+?(\b\w\w+?\b)")

        no_repeated_words = True

        for para in paras:
            # Are there any 'pairs of words' in this paragraph? That is, two words
            # separated by whitespace.
            #
            # The search commences at the start of the paragraph. If it finds a
            # pair of words, it checks if they are both the same and processes as
            # appropriate. It then recommences the search of the paragraph for
            # more pairs at the second word of the pair previously matched. In that
            # sense it is doing overlapping matches of pairs of words. If re.findall(),
            # etc., are instead used with the re_dw above, they will only find
            # non-overlapping pairs thus missing some.

            # Start at beginning of the paragraph. After first pair of words matched,
            # 'start_at' will point to the first letter of the second word of that pair
            # and so on.

            start_at = 0

            if not (res := re_dw.search(para[start_at:])):
                # No pairs of words found in this paragraph so skip to next one.

                continue

            # Here when at least one pair of words found in a paragraph.

            while res := re_dw.search(para[start_at:]):
                # We have a pointer to a pair of words separated by whitespace.

                # Are the two words the same?

                if res.group(1) == res.group(2):
                    # Yes, they are repeated words.

                    no_repeated_words = False

                    # We want to output the repeated words roughly in the
                    # middle of a slice of the paragraph text.

                    # Get 'indx', the position of the first letter of the
                    # pair of words just identified in the 'para' string.

                    indx = para.index(res.group(0))

                    # Bump it up to be roughly the middle of the two words
                    # by adding the length of the first word.

                    indx += len(res.group(1))

                    # Get the endpoints of the slice of the paragraph string
                    # in which the repeated words are hopefully centered.

                    llim, rlim = get_centered_slice_endpoints(indx, para)

                    # Locate the repeated words in this slice for highlighting.

                    highlighted_segment_start = para[llim:rlim].index(res.group(0))
                    highlighted_segment_length = len(res.group(0))

                    # Decorate the slice of the paragraph with the repeated words.
                    output_record = decorate(
                        para[llim:rlim],
                        [(highlighted_segment_start, highlighted_segment_length)],
                        "red",
                    )

                    # Lop off any prefixing spaces at start of record so all records
                    # align neatly at left margin of the report.

                    indx = 0
                    while output_record[indx : indx + 1] == " ":
                        indx += 1
                    # We may be copying an unchanged record!
                    output_record = output_record[indx:]

                    print(output_record, file=string_out)

                # Continue searching paragraph for more word pairs. Search will
                # recommence from the second word of the pair we just looked at.

                start_at += res.start(2)

        # Here when no more paras to search

        if no_repeated_words:
            print("    no repeated words found in text\n", file=string_out)
        else:
            print(" ", file=string_out)

        template = "{}"
        print(template.format("-" * 80), file=string_out)

    ######################################################################
    # ellipses check
    ######################################################################

    def ellipses_check():
        print("ellipses check\n", file=string_out)

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

        re8 = re.compile(r"(^|[^\.])\.\.($|[^\.])")  # was becoming διαστειχων..

        # Do explicit check for give us some pudding ....
        re9 = re.compile(r"\s\.\.\.\.$")

        no_ellipses_found = True

        rec_cnt = 0
        line_number = 1
        for line in book:
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

                    print(make_a_report_record(line_number, line), file=string_out)

                rec_cnt += 1

            line_number += 1

        # Here when all lines in book read and checked

        if not verbose and rec_cnt > 5:
            # We've only output the first five lines so say how many more there are

            remaining = rec_cnt - 5
            print("    ...", remaining, "more", file=string_out)

        if no_ellipses_found:
            print("    no incorrect ellipse usage found in text\n", file=string_out)
        else:
            print(" ", file=string_out)

        template = "{}"
        print(template.format("-" * 80), file=string_out)

    ######################################################################
    # abandoned HTML tag check
    ######################################################################

    def html_check():
        print("abandoned HTML tag check\n", file=string_out)

        # Courtesy limit if user uploads fpgen source, etc.
        abandoned_HTML_tag_count = 0

        HTML_report = []
        re_tg = re.compile(r"<(?=[!/a-z]).*?(?<=[\"a-z/]|--)>")

        line_number = 1
        for line in book:
            if res := re_tg.search(line):
                if abandoned_HTML_tag_count < 10:
                    HTML_report.append(make_a_report_record(line_number, line))
                if abandoned_HTML_tag_count == 10:
                    HTML_report.append("         ...more")
                abandoned_HTML_tag_count += 1
            line_number += 1

        # If abandoned_HTML_tag_count > 10 then it looks like we are not dealing
        # with a plain text file afterall. Flag this then output the first 10
        # HTML tag lines encountered.

        if abandoned_HTML_tag_count > 10:
            template = "note: source file not plain text: {} lines with markup\n"
            print(template.format(abandoned_HTML_tag_count), file=string_out)

        for record in HTML_report:
            print(record, file=string_out)

        if abandoned_HTML_tag_count == 0:
            print("    no abandoned HTML tags found in text\n", file=string_out)
        else:
            print(" ", file=string_out)

        template = "{}"
        print(template.format("-" * 80), file=string_out)

    ######################################################################
    # Unicode numeric character references check.
    ######################################################################

    def uniocode_numeric_character_check():
        print("unicode numeric character references check\n", file=string_out)

        # Courtesy limit if user uploads fpgen source, etc.
        numeric_char_reference_count = 0

        numeric_char_report = []
        re_unicode = re.compile(r"(&#[0-9]{1,4};|&#x[0-9a-fA-F]{1,4};)")

        rec_cnt = 0
        line_number = 1
        for line in book:
            if res := re_unicode.search(line):
                if verbose or numeric_char_reference_count < 5:
                    print(make_a_report_record(line_number, line), file=string_out)

                # Continue counting unicode numeric character references
                numeric_char_reference_count += 1

            line_number += 1

        if not verbose and numeric_char_reference_count > 5:
            # We've only output the first five lines with such references
            # so say how many more there are.

            remaining = numeric_char_reference_count - 5
            print("    ...", remaining, "more", file=string_out)

        if numeric_char_reference_count == 0:
            print(
                "    no unicode numeric character references found\n", file=string_out
            )
        else:
            print(" ", file=string_out)

        template = "{}"
        print(template.format("-" * 80), file=string_out)

    ######################################################################
    # dash review
    ######################################################################

    def dash_repl_re0c(matchobj):
        return matchobj.group(1) + "—" + matchobj.group(2)

    def dash_repl_re00(matchobj):
        return matchobj.group(1) + matchobj.group(2)

    def dash_review():
        print("hyphen/dashes check", file=string_out)

        # The algorithm used below is adopted from the one Roger Franks uses in
        # his Go version of PPTXT for the PPWB. It makes a copy of the book and
        # runs multiple passes over the copy. The first set of passes protects
        # what is allowed by overwriting them. The final pass categorises any
        # dashes that remain and flags them in the report.

        no_suspect_dashes_found = True
        rec_cnt = 0

        ####
        # In the PPWB Go version of PPTXT, Roger qualifies and protects the following dash characters & sequences:
        #    	- hyphen minus (keyboard "-")
        #              allow these between two letters [\p{L}‐\p{L}]
        #              allow 8 or more of these as a separator [‐{8,}]
        #    ‐ hyphen
        #              allow these between two letters [\p{L}‐\p{L}]
        #              allow 8 or more of these as a separator [‐{8,}]
        #    ‑ non-breaking hyphen
        #              allow these between two letters [\p{L}‐\p{L}]
        #    ‒ figure dash (i.e. to connect digits in a phone number)
        #              allow these between two numbers [\p{Nd}‒\p{Nd}]
        #    – en dash (to show a range of numbers)
        #              allow these between two numbers \p{Nd}–\p{Nd}
        #              allow these between two numbers \p{Nd}\s–\s\p{Nd}
        #    — em dash
        #              allow patterns:
        #                   [\p{L}—\p{L}] between letters with no spacing
        #                       My favorite food—pizza—originated in Italy.
        #                       My granddaughter—Kenzie—plays volleyball.
        #                   [\p{Ll}—\p{Pe}] between lower-case letter and closing punctuation
        #                       “What if we—”
        #                   \p{Ll}— \p{Lu} lower-case letter, en dash, space, upper-case letter
        #                       If you tell him— Wait, I will give you this.
        #
        # These are dash characters Roger flags
        #   - HYPHEN-MINUS
        #   ֊ ARMENIAN HYPHEN
        #   ־ HEBREW PUNCTUATION MAQAF
        #   ᐀ CANADIAN SYLLABICS HYPHEN
        #        ᠆    MONGOLIAN TODO SOFT HYPHEN
        #   ‐ HYPHEN
        #   ‑ NON-BREAKING HYPHEN
        #   ‒ FIGURE DASH
        #   – EN DASH
        #   — EM DASH
        #   ― HORIZONTAL BAR
        #   ⸗ DOUBLE OBLIQUE HYPHEN
        #   ⸚ HYPHEN WITH DIAERESIS
        #   ⸺ TWO-EM DASH
        #   ⸻ THREE-EM DASH
        #   ⹀ DOUBLE HYPHEN
        #   〜 WAVE DASH
        #   〰 WAVY DASH
        #   ゠ KATAKANA-HIRAGANA DOUBLE HYPHEN
        #   ︱ PRESENTATION FORM FOR VERTICAL EM DASH
        #   ︲ PRESENTATION FORM FOR VERTICAL EN DASH ﹘ SMALL EM DASH
        #   ﹣ SMALL HYPHEN-MINUS
        #   － FULLWIDTH HYPHEN-MINUS
        ####

        # INITIAL PASSES: protect what is allowed by overwriting lines in a copy of the book.

        dbuf = book.copy()

        # Regexes for the checks that will be made on lines in our copy (dbuf[])

        re00 = re.compile(r"\p{L}-\p{L}")  # hyphen-minus between two letters
        re01 = re.compile(r"\p{L}‐\p{L}")  # hyphen between two letters
        re02 = re.compile(r"-{8,}")  # hyphen-minus when 8 or more act as a separator
        re03 = re.compile(r"\p{L}‑\p{L}")  # non-breaking hyphen between two letters
        re04 = re.compile(r"\p{Nd}‒\p{Nd}")  # figure dash between two digitss
        re05 = re.compile(r"\p{Nd}–\p{Nd}")  # en-dash between two digits
        re06 = re.compile(
            r"\p{Nd}\s–\s\p{Nd}"
        )  # en-dash with spaces between two digits
        re07 = re.compile(r"\p{L}—\p{L}")  # em-dash between letters with no spacing
        re08 = re.compile(
            r"[\p{Ll}I]—\p{P}\s*$"
        )  # em-dash between lower-case letter or 'I' and final punctuation [{Pf}?]
        re09 = re.compile(
            r"\p{Ll}— \p{Lu}"
        )  # lower-case letter, em-dash, space, upper-case letter
        re0a = re.compile(r"—\s*$")  # em-dash can end a line if verbose not selected
        re0b = re.compile(
            r"\s——\s"
        )  # deleted words E.g. "as soon as Mr. —— had left the ship"
        re0c = re.compile(r"([^—])——([^—])")  # consider exactly two em-dashes as one
        re0d = re.compile(
            r"\p{Zs}*—"
        )  # see below to allow em-dash to start a paragraph.

        # The dashes we recognise

        ch_hm = "-"  # hyphen-minus
        ch_hy = "‐"  # hyphen
        ch_nb = "‑"  # non-breaking hyphen
        ch_fd = "‒"  # figure dash
        ch_en = "–"  # endash
        ch_em = "—"  # emdash

        # First pass allows em-dash to start a paragraph.

        # The loop below assumes a paragraph starts after an empty line, which
        # is generally the case, and goes through the book line by line looking
        # for them.
        #
        # Deal with the special case of the first line of the file being the
        # start of a paraqraph; i.e. it is not preceded by a blank line.

        indx = 0  # indx is the line number - 1
        while indx < len(dbuf) - 1:
            # Look for the presence of the special case.

            if indx == 0 and re0d.match(dbuf[indx]):
                # Special case.

                dbuf[indx] = dbuf[indx].replace("—", "", 1)

            else:
                # General case. I.e. paragraphs preceded by an empty line OR
                # the first line of the file contains text which does not
                # start with an em-dash.
                #
                # The purpose of the loop is to obfuscate an em-dash if it
                # appears at the start of a paragraph. NB em-dash can be
                # separated from the left-margin by one or more Unicode
                # space characters.

                if dbuf[indx] == "" and re0d.match(dbuf[indx + 1]):
                    dbuf[indx + 1] = dbuf[indx + 1].replace("—", "", 1)

            indx += 1

        # Go through the book line by line again and obfuscate valid occurrences
        # of Unicode dash characters. This is another of the initial passes.
        #
        # The order of execution of these replacements on a line is important!

        indx = 0  # indx is the line number - 1
        while indx < len(dbuf):
            dbuf[indx] = dbuf[indx].replace("_", "")
            dbuf[indx] = re0b.sub(" XX ", dbuf[indx])
            dbuf[indx] = re0c.sub(dash_repl_re0c, dbuf[indx])
            dbuf[indx] = re00.sub("", dbuf[indx])
            dbuf[indx] = re01.sub("", dbuf[indx])
            dbuf[indx] = re02.sub("", dbuf[indx])
            dbuf[indx] = re03.sub("", dbuf[indx])
            dbuf[indx] = re04.sub("", dbuf[indx])
            dbuf[indx] = re05.sub("", dbuf[indx])
            dbuf[indx] = re06.sub("", dbuf[indx])
            dbuf[indx] = re07.sub("", dbuf[indx])
            dbuf[indx] = re08.sub("", dbuf[indx])
            dbuf[indx] = re09.sub("", dbuf[indx])
            if not verbose:
                dbuf[indx] = re0a.sub("", dbuf[indx])

            indx += 1

        # FINAL PASS: flag what remains.

        refp01 = re.compile(r"\p{Pd}")  # any dash
        refp02 = re.compile(r"(\p{Pd}\p{Pd}+)")  # consecutive dashes

        a_hh = []
        a_hm = []
        a_hy = []
        a_nb = []
        a_fd = []
        a_en = []
        a_em = []
        a_un = []

        dash_suspects_found = False
        indx = 0

        while indx < len(dbuf):
            line = dbuf[indx]

            # Does line contain any dashes?

            if refp01.search(line):
                # Line has dashes so generate output records to flag these.

                dash_suspects_found = True
                not_consecutive_dashes = True

                if res := refp02.search(
                    line
                ):  # Found consecutive dashes (of any kind).
                    a_hh.append(make_a_report_record(indx + 1, book[indx]))
                    # Delete dash(es) just found before unrecognised dash check
                    line = line.replace(res.group(0), "")
                    not_consecutive_dashes = False
                if ch_hm in line and not_consecutive_dashes:  # hyphen-minus
                    a_hm.append(make_a_report_record(indx + 1, book[indx]))
                    # Delete dash(es) just found before unrecognised dash check
                    line = line.replace(ch_hm, "")
                if ch_hy in line:  # hyphen
                    a_hy.append(make_a_report_record(indx + 1, book[indx]))
                    # Delete dash(es) just found before unrecognised dash check
                    line = line.replace(ch_hy, "")
                if ch_nb in line:  # non-breaking hyphen
                    a_nb.append(make_a_report_record(indx + 1, book[indx]))
                    # Delete dash(es) just found before unrecognised dash check
                    line = line.replace(ch_nb, "")
                if ch_fd in line:  # figure dash
                    a_fd.append(make_a_report_record(indx + 1, book[indx]))
                    # Delete dash(es) just found before unrecognised dash check
                    line = line.replace(ch_fd, "")
                if ch_en in line:  # endash
                    a_en.append(make_a_report_record(indx + 1, book[indx]))
                    # Delete dash(es) just found before unrecognised dash check
                    line = line.replace(ch_en, "")
                if ch_em in line:  # emdash
                    a_em.append(make_a_report_record(indx + 1, book[indx]))
                    # Delete dash(es) just found before unrecognised dash check
                    line = line.replace(ch_em, "")
                if refp01.search(line):
                    # If we get here we found an unrecognised dash in the line
                    a_un.append(make_a_report_record(indx + 1, book[indx]))

            indx += 1

        if len(a_hh) > 0:
            # If "--" detected report only the first five.

            print("\n adjacent dashes:", file=string_out)
            counthh = 0
            for record in a_hh:
                if "--" in record:
                    if counthh < 5:
                        print(record, file=string_out)
                    if counthh == 5:
                        print(
                            '    [book seems to use "--" as em-dash so not reporting these further]',
                            file=string_out,
                        )

                    # Keep counting "--" records even when not logging them (see loop below).
                    counthh += 1

            # Report other consecutive dashes

            count = 0
            for record in a_hh:
                if not "--" in record:
                    if verbose:
                        # Print all records.
                        print(record, file=string_out)
                    else:
                        # Print only a sample of records.
                        if count < 10:
                            print(record, file=string_out)
                        if count == 10:
                            template = "  ...{} more"
                            print(
                                template.format(len(a_hh) - 10 - counthh),
                                file=string_out,
                            )
                            break

                        count += 1

        # Report hyphen-minus

        if len(a_hm) > 0:
            print(" \n hyphen-minus:", file=string_out)

            count = 0
            for record in a_hm:
                if count < 10 or verbose:
                    print(record, file=string_out)
                if count == 10 and not verbose:
                    template = "  ...{} more"
                    print(template.format(len(a_hm) - 10), file=string_out)
                    break

                count += 1

        # Report hyphen

        if len(a_hy) > 0:
            print(" \n hyphen:", file=string_out)

            count = 0
            for record in a_hy:
                if count < 10 or verbose:
                    print(record, file=string_out)
                if count == 10 and not verbose:
                    template = "  ...{} more"
                    print(template.format(len(a_hy) - 10), file=string_out)
                    break

                count += 1

        # Report non-breaking hyphen

        if len(a_nb) > 0:
            print(" \n non-breaking hyphen:", file=string_out)

            count = 0
            for record in a_nb:
                if count < 10 or verbose:
                    print(record, file=string_out)
                if count == 10 and not verbose:
                    template = "  ...{} more"
                    print(template.format(len(a_nb) - 10), file=string_out)
                    break

                count += 1

        # Report figure dash

        if len(a_fd) > 0:
            print(" \n figure dash:", file=string_out)

            count = 0
            for record in a_fd:
                if count < 10 or verbose:
                    print(record, file=string_out)
                if count == 10 and not verbose:
                    template = "  ...{} more"
                    print(template.format(len(a_fd) - 10), file=string_out)
                    break

                count += 1

        # Report en-dash

        if len(a_en) > 0:
            print(" \n en-dash:", file=string_out)

            count = 0
            for record in a_en:
                if count < 10 or verbose:
                    print(record, file=string_out)
                if count == 10 and not verbose:
                    template = "  ...{} more"
                    print(template.format(len(a_en) - 10), file=string_out)
                    break

                count += 1

        # Report em-dash

        if len(a_em) > 0:
            print(" \n em-dash:", file=string_out)

            count = 0
            for record in a_em:
                if count < 10 or verbose:
                    print(record, file=string_out)
                if count == 10 and not verbose:
                    template = "  ...{} more"
                    print(template.format(len(a_em) - 10), file=string_out)
                    break

                count += 1

        # Report unrecognised dash

        if len(a_un) > 0:
            print(" \n unrecognised dash:", file=string_out)

            count = 0
            for record in a_un:
                if count < 10 or verbose:
                    print(record, file=string_out)
                if count == 10 and not verbose:
                    template = "  ...{} more"
                    print(template.format(len(a_un) - 10), file=string_out)
                    break

                count += 1

        if not dash_suspects_found:
            print("\n    no dash suspects found in text", file=string_out)

        template = "\n{}"
        print(template.format("-" * 80), file=string_out)

    ######################################################################
    # curly quote check (positional, not using a state machine)
    ######################################################################

    def curly_quote_check():
        print("curly quote check", file=string_out)

        # Report floating quotes - “” and ‘’ types.

        r0a = re.compile(r" [“”\‘\’] ")
        r0b = re.compile(r"^[“”\‘\’] ")
        r0c = re.compile(r" [“”\‘\’]$")

        first_match = True

        rec_count_fq = 0
        line_number = 1
        for line in book:
            if r0a.search(line) or r0b.search(line) or r0c.search(line):
                if first_match:
                    first_match = False
                    print(" \nfloating quote (single or double)", file=string_out)
                if rec_count_fq < 5 or verbose:
                    print(make_a_report_record(line_number, line), file=string_out)

                rec_count_fq += 1

            line_number += 1

        if rec_count_fq >= 5 and not verbose:
            template = "  ...{} more floating quote reports"
            print(template.format(rec_count_fq - 5), file=string_out)

        # Report 'wrong direction' quotes

        r1a = re.compile(r"[\.,;!?]+?[‘“]")  # some text.“
        r1b = re.compile(r"\p{L}+?[\‘\“]")  # some text‘
        r1c = re.compile(r"”[\p{L}]")  # ”some text

        first_match = True

        rec_count_qd = 0
        line_number = 1
        for line in book:
            if r1a.search(line) or r1b.search(line) or r1c.search(line):
                if first_match:
                    first_match = False
                    print(" \nquote direction", file=string_out)

                if rec_count_qd < 5 or verbose:
                    print(make_a_report_record(line_number, line), file=string_out)

                rec_count_qd += 1

            line_number += 1

        if rec_count_qd >= 5 and not verbose:
            template = "  ...{} more quote direction reports"
            print(template.format(rec_count_qd - 5), file=string_out)

        # Report misplaced double quotes. These checks are done
        # on paragraphs, not lines as above.

        # Look for opening double quotes first.

        first_match_oq = True
        rec_count_qm = 0

        for para in paras:
            indx = 0
            while indx < len(para):
                if para[indx : indx + 1] == "“":
                    # We have an opening double quote.

                    if indx == 0:
                        # An opening quote at start of paragraph
                        prev_char = ""
                    else:
                        prev_char = para[indx - 1 : indx]

                    # Look at previous character to see if opening
                    # double quote looks misplaced. Allow:
                    #
                    #   sp quote commonly after a space
                    #   —  quote commonly after emdash
                    #   (  quote in parenthesis
                    #   _  quoted heading, etc., in italic
                    #   =  quoted heading, etc., in bold

                    if not (
                        prev_char == ""
                        or prev_char == " "
                        or prev_char == "—"
                        or prev_char == "("
                        or prev_char == "_"
                        or prev_char == "="
                    ):
                        # Output this header once only when first suspect found.
                        if first_match_oq:
                            first_match_oq = False
                            print(" \npossible misplaced “", file=string_out)

                        # Output suspect quote to log with some surrounding context

                        if rec_count_qm < 5 or verbose:
                            llim, rlim = get_centered_slice_endpoints(indx, para)
                            output_record = "  " + para[llim:rlim]
                            print(output_record, file=string_out)

                        rec_count_qm += 1

                indx += 1

        if rec_count_qm >= 5 and not verbose:
            template = "  ...{} more possible misplaced “"
            print(template.format(rec_count_qm - 5), file=string_out)

        # Now look for closing quotes.

        first_match_cq = True
        rec_count_qm = 0

        re_pu = re.compile(r"\p{P}")

        for para in paras:
            indx = 0
            while indx < len(para):
                if para[indx : indx + 1] == "”":
                    # We have a closing double quote.

                    if indx == len(para) - 1:
                        # A closing quote at end of paragraph
                        next_char = ""
                    else:
                        next_char = para[indx + 1 : indx + 2]

                    # Look at next character to see if closing
                    # double quote looks misplaced. Allow:
                    #
                    #   Any punctuation.
                    #   sp quote commonly before a space
                    #   —  quote commonly before emdash
                    #   )  quote in parenthesis
                    #   _  quoted heading, etc., in italic
                    #   =  quoted heading, etc., in bold

                    punctuation = re_pu.match(next_char)
                    if not (
                        next_char == ""
                        or next_char == " "
                        or next_char == "—"
                        or next_char == "("
                        or next_char == "_"
                        or next_char == "="
                        or punctuation
                    ):
                        # Output this header once only when first suspect found.
                        if first_match_cq:
                            first_match_cq = False
                            print(" \npossible misplaced ”", file=string_out)

                        # Output the suspect to the log with some surrounding context

                        if rec_count_qm < 5 or verbose:
                            llim, rlim = get_centered_slice_endpoints(indx, para)
                            output_record = "  " + para[llim:rlim]
                            print(output_record, file=string_out)

                        rec_count_qm += 1

                indx += 1

        if rec_count_qm >= 5 and not verbose:
            template = "  ...{} more possible misplaced ”"
            print(template.format(rec_count_qm - 5), file=string_out)

        if rec_count_fq == 0 and rec_count_qd == 0 and rec_count_qm == 0:
            print("\n    no suspect curly quotes found in text", file=string_out)

        template = "\n{}"
        print(template.format("-" * 80), file=string_out)

    def build_scanno_dictionary():
        # List of common scannos. Add additions to end of the list.
        # Duplicates will be dealt with when building the dictionary.

        scannos_misspelled = [
            "1gth",
            "1lth",
            "1oth",
            "1Oth",
            "2gth",
            "2ist",
            "2lst",
            "oa",
            "po",
            "2Oth",
            "2OTH",
            "2oth",
            "3lst",
            "3Oth",
            "3oth",
            "abead",
            "ablc",
            "Abont",
            "abovc",
            "abscnt",
            "abseut",
            "acadernic",
            "acbe",
            "acccpt",
            "accnse",
            "accornpany",
            "accusc",
            "accustorn",
            "achc",
            "aclie",
            "actiou",
            "activc",
            "actnal",
            "adinire",
            "adinit",
            "admirc",
            "adnlt",
            "adrnire",
            "adrnission",
            "adrnit",
            "advicc",
            "advisc",
            "affcct",
            "aftcr",
            "Aftcr",
            "aftemoon",
            "agaiu",
            "Agaiu",
            "Agaiust",
            "agam",
            "Agam",
            "Agamst",
            "agc",
            "agcncy",
            "agcnt",
            "agencv",
            "ageucy",
            "ageut",
            "agrcc",
            "agreernent",
            "ahcad",
            "ahke",
            "ahle",
            "Ahont",
            "Ahout",
            "ahout",
            "ahove",
            "ahroad",
            "ahsent",
            "ahve",
            "aiin",
            "ainong",
            "ainount",
            "ainuse",
            "airn",
            "A-Iy",
            "aliead",
            "alikc",
            "alinost",
            "alivc",
            "aln",
            "alonc",
            "alond",
            "aloue",
            "aloug",
            "alrnost",
            "altbough",
            "altemative",
            "alwavs",
            "amd",
            "amnse",
            "amonnt",
            "amoug",
            "amouut",
            "amusc",
            "ane",
            "angcr",
            "anglc",
            "angrv",
            "aniinal",
            "anirnal",
            "annnal",
            "annov",
            "annt",
            "Anotber",
            "anotber",
            "Anothcr",
            "Anotlier",
            "answcr",
            "anthor",
            "antnmn",
            "anv",
            "Anv",
            "anvhow",
            "anvone",
            "anvwav",
            "anybow",
            "anyliow",
            "anyonc",
            "appcal",
            "appcar",
            "applv",
            "appointrnent",
            "arca",
            "arcb",
            "arcli",
            "argne",
            "arguc",
            "argurnent",
            "arin",
            "ariny",
            "arisc",
            "armv",
            "arn",
            "arnbition",
            "arnbitious",
            "arnong",
            "arnongst",
            "arnount",
            "arnuse",
            "Aronnd",
            "aronnd",
            "arouud",
            "Arouud",
            "arrangernent",
            "arrcst",
            "arrivc",
            "arrn",
            "arrny",
            "asb",
            "asharned",
            "asidc",
            "aslccp",
            "asli",
            "aspcct",
            "asscss",
            "assct",
            "assernbly",
            "assessrnent",
            "assnme",
            "assuine",
            "assumc",
            "assurne",
            "assurnption",
            "atrnosphere",
            "attacb",
            "attacli",
            "attcnd",
            "atternpt",
            "atteud",
            "au",
            "aud",
            "Aud",
            "augle",
            "augry",
            "auimal",
            "Auother",
            "auswer",
            "autbor",
            "autlior",
            "autuinn",
            "autumu",
            "auturnn",
            "auuoy",
            "auut",
            "auuual",
            "Auv",
            "Auy",
            "auy",
            "auyhow",
            "auyoue",
            "auyway",
            "avenne",
            "aveuue",
            "awakc",
            "awarc",
            "awav",
            "babit",
            "babv",
            "bair",
            "bakc",
            "balf",
            "bandle",
            "bappen",
            "bappy",
            "barc",
            "barden",
            "bardly",
            "Barly",
            "barm",
            "barrcl",
            "bas",
            "basc",
            "basiu",
            "baskct",
            "basm",
            "basten",
            "batb",
            "batbe",
            "bathc",
            "batli",
            "batlie",
            "batred",
            "battlc",
            "bauk",
            "baok",
            "bav",
            "bave",
            "baving",
            "Bc",
            "bc",
            "bcam",
            "bcan",
            "bcar",
            "bcard",
            "bcast",
            "bcat",
            "bcauty",
            "Bccausc",
            "bccomc",
            "bcd",
            "bcforc",
            "Bcforc",
            "Bcfore",
            "Bcgin",
            "bcgin",
            "Bcgiu",
            "bchavc",
            "bchind",
            "bcing",
            "bclicf",
            "bcll",
            "bclong",
            "bclow",
            "bclt",
            "bcnd",
            "bcrry",
            "bcsidc",
            "bcst",
            "bcttcr",
            "Bctwccn",
            "bcyond",
            "beain",
            "beal",
            "bealtb",
            "beanty",
            "beap",
            "bearn",
            "beart",
            "beautv",
            "beaven",
            "beavy",
            "bebave",
            "bebind",
            "Becanse",
            "becoine",
            "becond",
            "becorne",
            "bedroorn",
            "Beforc",
            "Begiu",
            "begiu",
            "Begm",
            "begm",
            "behef",
            "behiud",
            "behmd",
            "beigbt",
            "beiug",
            "beliave",
            "beliind",
            "bello",
            "beloug",
            "belp",
            "belped",
            "bemg",
            "bence",
            "ber",
            "bere",
            "berrv",
            "Betweeu",
            "beud",
            "bevond",
            "beyoud",
            "bhnd",
            "bigb",
            "bigbly",
            "bim",
            "bire",
            "birtb",
            "birtli",
            "bis",
            "bitc",
            "bittcr",
            "biud",
            "bladc",
            "blaine",
            "blamc",
            "blarne",
            "blccd",
            "blcss",
            "bliud",
            "blmd",
            "blne",
            "bloodv",
            "bluc",
            "bmd",
            "bncket",
            "bndget",
            "bnild",
            "bnilt",
            "bnnch",
            "bnndle",
            "Bnow",
            "bnrn",
            "bnrst",
            "bnry",
            "bns",
            "bnsh",
            "bnsy",
            "bnt",
            "Bnt",
            "bntter",
            "bntton",
            "bny",
            "bodv",
            "bole",
            "bollow",
            "boly",
            "bome",
            "bomes",
            "bonest",
            "bonnd",
            "bonor",
            "bope",
            "bordcr",
            "borse",
            "bost",
            "bot",
            "botb",
            "Botb",
            "botel",
            "Botli",
            "botli",
            "bottlc",
            "bottoin",
            "bottorn",
            "boue",
            "bour",
            "bouse",
            "boused",
            "bouses",
            "bouud",
            "bov",
            "bowever",
            "braiu",
            "brancb",
            "brancli",
            "brauch",
            "bravc",
            "brcad",
            "brcak",
            "brcath",
            "breatb",
            "breatli",
            "bribc",
            "bricf",
            "bridgc",
            "brigbt",
            "briglit",
            "brihe",
            "briug",
            "brmg",
            "brnsh",
            "browu",
            "brusb",
            "brusli",
            "buckct",
            "buge",
            "buncb",
            "buncli",
            "bundlc",
            "bunger",
            "burry",
            "burt",
            "buru",
            "burv",
            "busb",
            "busiiicss",
            "busli",
            "busv",
            "buttcr",
            "buttou",
            "buuch",
            "buudle",
            "buv",
            "bv",
            "Bv",
            "Bven",
            "cach",
            "cagc",
            "cagcr",
            "cailing",
            "cainp",
            "cakc",
            "calin",
            "calrn",
            "canse",
            "camo",
            "carc",
            "carccr",
            "carly",
            "carn",
            "carnp",
            "carnpaign",
            "carrv",
            "carth",
            "casb",
            "casc",
            "casc",
            "casily",
            "casli",
            "castlc",
            "casy",
            "catcb",
            "catcli",
            "cattlc",
            "cau",
            "Cau",
            "caual",
            "causc",
            "cavc",
            "cbain",
            "cbair",
            "cbalk",
            "cbance",
            "Cbange",
            "cbange",
            "cbarm",
            "cbeap",
            "cbeat",
            "cbeck",
            "cbeer",
            "cbeese",
            "cbest",
            "cbief",
            "cbild",
            "cboice",
            "cboose",
            "cburcb",
            "ccnt",
            "ccntcr",
            "ccntrc",
            "cdgc",
            "cerernony",
            "ceut",
            "ceuter",
            "ceutre",
            "cf",
            "cffcct",
            "cffort",
            "chairrnan",
            "chaiu",
            "chancc",
            "changc",
            "Changc",
            "CHAPTEE",
            "chargc",
            "charrn",
            "chauce",
            "chauge",
            "Chauge",
            "chcap",
            "chcck",
            "chcst",
            "chent",
            "chff",
            "chicf",
            "chirnney",
            "chmb",
            "chnrch",
            "choicc",
            "choosc",
            "circlc",
            "circurnstance",
            "cithcr",
            "cither",
            "citv",
            "claas",
            "claiin",
            "clairn",
            "clav",
            "clcan",
            "clcar",
            "clcct",
            "clcvcr",
            "cldcr",
            "cleau",
            "cliain",
            "cliair",
            "clialk",
            "cliance",
            "Cliange",
            "cliange",
            "cliarge",
            "cliarm",
            "clieap",
            "clieat",
            "clieck",
            "clieer",
            "cliest",
            "clieut",
            "cliief",
            "cliild",
            "cliinb",
            "climh",
            "clioice",
            "clioose",
            "clirnb",
            "clnb",
            "clond",
            "Closc",
            "closc",
            "clotb",
            "clotbe",
            "clothc",
            "clotli",
            "clotlie",
            "clsc",
            "cluh",
            "cmcrgc",
            "cmpirc",
            "cmploy",
            "cmpty",
            "cnablc",
            "cncmy",
            "cnd",
            "cnjoy",
            "cnough",
            "cnp",
            "cnre",
            "cnrl",
            "cnrse",
            "cnrve",
            "cnstom",
            "cnsurc",
            "cnt",
            "cntcr",
            "cntirc",
            "cntry",
            "cnvy",
            "coarsc",
            "coffcc",
            "coinb",
            "Coine",
            "coine",
            "coiu",
            "colonr",
            "colonv",
            "colouy",
            "comh",
            "commou",
            "concem",
            "concemed",
            "confirrn",
            "congh",
            "conld",
            "Conld",
            "connt",
            "connty",
            "conple",
            "conrse",
            "conrt",
            "Considcr",
            "consin",
            "coppcr",
            "copv",
            "cornb",
            "cornbination",
            "cornbine",
            "corncr",
            "corne",
            "Corne",
            "cornfort",
            "corning",
            "cornpanion",
            "cornpanionship",
            "cornpany",
            "cornpare",
            "cornparison",
            "cornpete",
            "cornpetitor",
            "cornplain",
            "cornplaint",
            "cornplete",
            "cornpletely",
            "cornpletion",
            "cornplex",
            "cornplicate",
            "cornplication",
            "cornponent",
            "cornpose",
            "cornposition",
            "coru",
            "coruer",
            "cottou",
            "cou",
            "cougb",
            "cougli",
            "couldnt",
            "countv",
            "couplc",
            "coursc",
            "Cousider",
            "cousiu",
            "couut",
            "couuty",
            "covcr",
            "cqual",
            "crasb",
            "crasli",
            "crcam",
            "crcatc",
            "creain",
            "crearn",
            "criine",
            "crimc",
            "crirne",
            "crirninal",
            "criticisrn",
            "crnel",
            "crnsh",
            "crowu",
            "crror",
            "crucl",
            "crusb",
            "crusli",
            "crv",
            "cscapc",
            "cstatc",
            "curc",
            "cursc",
            "curvc",
            "custoin",
            "custorn",
            "custornary",
            "custorner",
            "cvcn",
            "cvcnt",
            "cvcr",
            "cvcry",
            "cver",
            "cvil",
            "cxact",
            "cxccpt",
            "cxccss",
            "cxcitc",
            "cxcusc",
            "cxist",
            "cxpcct",
            "cxpcrt",
            "cxtcnd",
            "cxtcnt",
            "cxtra",
            "cyc",
            "cycd",
            "dailv",
            "dainage",
            "dainp",
            "damagc",
            "dancc",
            "dangcr",
            "darc",
            "darkcn",
            "darkeu",
            "darnage",
            "darnp",
            "datc",
            "dauce",
            "dauger",
            "dav",
            "davlight",
            "dc",
            "dcad",
            "dcal",
            "dcar",
            "dcath",
            "dcbatc",
            "dcbt",
            "dccadc",
            "dccay",
            "dcccit",
            "dccd",
            "dccidc",
            "dccp",
            "dccpcn",
            "dccr",
            "dcfcat",
            "dcfcnd",
            "dcfinc",
            "dcgrcc",
            "dclay",
            "dclivcred",
            "dcmand",
            "dcny",
            "dcpcnd",
            "dcpth",
            "dcputy",
            "dcrivc",
            "dcscrt",
            "dcsign",
            "dcsirc",
            "dcsk",
            "dctail",
            "dcvicc",
            "dcvil",
            "deatb",
            "deatli",
            "decav",
            "deepeu",
            "defeud",
            "defiue",
            "defme",
            "dehate",
            "dehates",
            "deht",
            "deinand",
            "delav",
            "demaud",
            "denv",
            "departrnent",
            "depeud",
            "depnty",
            "deptb",
            "deptli",
            "deputv",
            "dernand",
            "dernocratic",
            "dernonstrate",
            "desigu",
            "deterrnine",
            "deuy",
            "developrnent",
            "diarnond",
            "dic",
            "didnt",
            "dinc",
            "dinncr",
            "dircct",
            "disb",
            "discornfort",
            "disli",
            "disrniss",
            "ditcb",
            "ditcli",
            "diue",
            "diuuer",
            "divc",
            "dividc",
            "dme",
            "dmner",
            "dnck",
            "dne",
            "dnll",
            "dnring",
            "Dnring",
            "dnst",
            "dnty",
            "docurnent",
            "doesnt",
            "donble",
            "donbt",
            "donkev",
            "dont",
            "dornestic",
            "doublc",
            "douhle",
            "douht",
            "dowu",
            "Dowu",
            "dozcn",
            "dozeu",
            "drawcr",
            "drcam",
            "drcss",
            "dreain",
            "drearn",
            "driuk",
            "drivc",
            "drivcr",
            "drmk",
            "drng",
            "drnm",
            "drowu",
            "druin",
            "drurn",
            "drv",
            "duc",
            "duriug",
            "Duriug",
            "durmg",
            "Durmg",
            "dutv",
            "eacb",
            "Eacb",
            "Eack",
            "Eacli",
            "eacli",
            "eam",
            "eamest",
            "earlv",
            "Earlv",
            "eartb",
            "eartli",
            "earu",
            "easilv",
            "eastem",
            "easv",
            "econornic",
            "econorny",
            "Ee",
            "Eecause",
            "Eeep",
            "Eefore",
            "Eegin",
            "Eetween",
            "Eill",
            "einerge",
            "einpire",
            "einploy",
            "einpty",
            "eitber",
            "eitlier",
            "elernent",
            "emplov",
            "emptv",
            "enahle",
            "eneiny",
            "enemv",
            "energv",
            "enerny",
            "enjov",
            "enongh",
            "enougb",
            "enougli",
            "ensnre",
            "entrv",
            "environrnent",
            "envv",
            "Eobert",
            "Eome",
            "Eoth",
            "eqnal",
            "equiprnent",
            "ernerge",
            "ernphasis",
            "ernpire",
            "ernploy",
            "ernpty",
            "establishrnent",
            "estirnate",
            "euable",
            "eud",
            "euemy",
            "euergy",
            "eujoy",
            "euough",
            "eusure",
            "Eut",
            "euter",
            "eutire",
            "eutry",
            "euvy",
            "Evcn",
            "everv",
            "Eveu",
            "eveu",
            "eveut",
            "exarnination",
            "exarnine",
            "exarnple",
            "excnse",
            "experirnent",
            "extemal",
            "exteud",
            "exteut",
            "extrerne",
            "extrernely",
            "Ey",
            "facc",
            "fadc",
            "faine",
            "fainily",
            "fainous",
            "fairlv",
            "faitb",
            "faitli",
            "faiut",
            "famc",
            "familv",
            "famons",
            "famt",
            "fancv",
            "fanlt",
            "farin",
            "fariner",
            "farmcr",
            "farne",
            "farniliar",
            "farnily",
            "farnous",
            "farrn",
            "farrner",
            "fastcn",
            "fasteu",
            "fatber",
            "fatc",
            "fathcr",
            "fatlier",
            "fattcn",
            "fatteu",
            "fau",
            "faucy",
            "favonr",
            "fcar",
            "fcast",
            "fcc",
            "fccd",
            "fccl",
            "fcllow",
            "fcncc",
            "fcvcr",
            "fcw",
            "Fcw",
            "feinale",
            "fernale",
            "feuce",
            "fhght",
            "ficld",
            "ficrcc",
            "figbt",
            "figlit",
            "fignre",
            "figurc",
            "filc",
            "filid",
            "filin",
            "finc",
            "fingcr",
            "finisb",
            "finisli",
            "firc",
            "firin",
            "firrn",
            "fisb",
            "fisli",
            "fiual",
            "fiud",
            "fiue",
            "fiuger",
            "fiuish",
            "flaine",
            "flamc",
            "flarne",
            "flasb",
            "flasli",
            "flesb",
            "flesli",
            "fligbt",
            "fliglit",
            "flonr",
            "flv",
            "fmal",
            "fmd",
            "fme",
            "fmger",
            "fmish",
            "fnel",
            "fnll",
            "fnlly",
            "fnn",
            "fnnd",
            "fnnny",
            "fnr",
            "fntnre",
            "focns",
            "forcc",
            "forcst",
            "forgct",
            "forhid",
            "forin",
            "forinal",
            "foriner",
            "formcr",
            "forrn",
            "forrnal",
            "forrner",
            "fortb",
            "fortli",
            "foud",
            "fraine",
            "framc",
            "frarne",
            "frarnework",
            "frcc",
            "frcczc",
            "frcsh",
            "freedorn",
            "freind",
            "fresb",
            "fresli",
            "fricnd",
            "frieud",
            "frigbt",
            "friglit",
            "frnit",
            "Froin",
            "froin",
            "fromt",
            "Frorn",
            "frorn",
            "frout",
            "frow",
            "frv",
            "fucl",
            "fullv",
            "fumish",
            "fumiture",
            "funnv",
            "furtber",
            "futurc",
            "fuu",
            "fuud",
            "fuuuy",
            "gaicty",
            "gaietv",
            "gaine",
            "gaiu",
            "gallou",
            "gamc",
            "garagc",
            "gardcn",
            "gardeu",
            "garne",
            "gatber",
            "gatc",
            "gathcr",
            "gatlier",
            "gav",
            "gcntlc",
            "gct",
            "gentlernan",
            "geutle",
            "givc",
            "Givc",
            "glorv",
            "gnard",
            "gness",
            "gnest",
            "gnide",
            "gnilt",
            "gnn",
            "goldcn",
            "goldeu",
            "govcrn",
            "govem",
            "govemment",
            "govemor",
            "governrnent",
            "goveru",
            "gracc",
            "graiu",
            "graud",
            "graut",
            "grav",
            "gravc",
            "grcasc",
            "grcat",
            "Grcat",
            "grccd",
            "grccn",
            "grcct",
            "grcy",
            "greeu",
            "grev",
            "griud",
            "grmd",
            "gronnd",
            "gronp",
            "grouud",
            "growtb",
            "growtli",
            "gth",
            "gucss",
            "gucst",
            "guidc",
            "guu",
            "hahit",
            "hake",
            "han",
            "handlc",
            "happcn",
            "happeu",
            "happv",
            "har",
            "hardcn",
            "hardeu",
            "hardlv",
            "harhor",
            "harin",
            "harrel",
            "harrn",
            "hase",
            "hasic",
            "hasin",
            "hasis",
            "hasket",
            "hastc",
            "hastcn",
            "hasteu",
            "hatc",
            "hathe",
            "hatrcd",
            "hattle",
            "haud",
            "haudle",
            "haug",
            "hav",
            "havc",
            "Havc",
            "Hc",
            "hc",
            "hcad",
            "hcal",
            "hcalth",
            "hcap",
            "hcar",
            "hcart",
            "hcat",
            "hcavcn",
            "hcavy",
            "hcight",
            "hcll",
            "hcllo",
            "hclp",
            "hcncc",
            "hcr",
            "hcrc",
            "hd",
            "heak",
            "heam",
            "hean",
            "heast",
            "heauty",
            "heaveu",
            "heavv",
            "hecause",
            "hecome",
            "hed",
            "heen",
            "hefore",
            "heg",
            "hegan",
            "hegin",
            "hehave",
            "hehind",
            "heid",
            "heing",
            "helief",
            "helieve",
            "helong",
            "helow",
            "helt",
            "hend",
            "henefit",
            "herry",
            "heside",
            "hest",
            "hetter",
            "hetween",
            "heuce",
            "heyond",
            "hfe",
            "hft",
            "hght",
            "hia",
            "hidc",
            "hie",
            "hig",
            "higber",
            "highlv",
            "hiii",
            "hiin",
            "hiln",
            "hin",
            "hindcr",
            "hirc",
            "hird",
            "hirn",
            "hirnself",
            "hirth",
            "hite",
            "hiuder",
            "hke",
            "hkely",
            "hlack",
            "hlade",
            "hlame",
            "hleed",
            "hless",
            "hlind",
            "hlock",
            "hlood",
            "hloody",
            "hlow",
            "hlue",
            "hmb",
            "hmder",
            "hmit",
            "hne",
            "hnge",
            "hnk",
            "hnman",
            "hnmble",
            "hnnger",
            "hnnt",
            "hnrry",
            "hnrt",
            "hnt",
            "hoast",
            "hoat",
            "hody",
            "hoil",
            "hoine",
            "holc",
            "holv",
            "homc",
            "honcst",
            "honr",
            "honse",
            "hopc",
            "horder",
            "horne",
            "hornecorning",
            "hornernade",
            "hornework",
            "horrow",
            "horsc",
            "hotcl",
            "hoth",
            "hottle",
            "hottom",
            "houest",
            "houor",
            "housc",
            "Howcvcr",
            "Howcver",
            "Howevcr",
            "hox",
            "hp",
            "hquid",
            "hrain",
            "hranch",
            "hrass",
            "hrave",
            "hread",
            "hreak",
            "hreath",
            "hrick",
            "hridge",
            "hrief",
            "hright",
            "hring",
            "hroad",
            "hrown",
            "hrush",
            "hst",
            "hsten",
            "httle",
            "hucket",
            "hudget",
            "hugc",
            "huild",
            "huinan",
            "huinble",
            "humblc",
            "humhle",
            "hundle",
            "hungcr",
            "hurn",
            "hurnan",
            "hurnble",
            "hurrv",
            "hurst",
            "hury",
            "hus",
            "husy",
            "hutter",
            "hutton",
            "huuger",
            "huut",
            "huy",
            "hve",
            "hving",
            "hy",
            "i3th",
            "i4th",
            "i5th",
            "i6th",
            "i7th",
            "i8th",
            "i9th",
            "ia",
            "icc",
            "idca",
            "idcal",
            "idlc",
            "ignorc",
            "iguore",
            "iie",
            "iii",
            "iiie",
            "iinage",
            "iinpact",
            "iinply",
            "iinpose",
            "iiow",
            "Ile",
            "Ilim",
            "I-low",
            "imagc",
            "implv",
            "imposc",
            "inad",
            "inadden",
            "inail",
            "inain",
            "inainly",
            "inajor",
            "inake",
            "inanage",
            "inanner",
            "inany",
            "inap",
            "inarch",
            "inark",
            "inarket",
            "inarry",
            "inass",
            "inaster",
            "inat",
            "inatch",
            "inatter",
            "inay",
            "inaybe",
            "incb",
            "incli",
            "incoine",
            "incomc",
            "incorne",
            "indccd",
            "ine",
            "ineal",
            "inean",
            "ineans",
            "ineat",
            "ineet",
            "inelt",
            "inend",
            "inental",
            "inercy",
            "inere",
            "inerely",
            "inerry",
            "inetal",
            "inethod",
            "inforin",
            "inforrn",
            "inforrnation",
            "iniddle",
            "inight",
            "inild",
            "inile",
            "inilk",
            "inill",
            "inind",
            "inine",
            "ininute",
            "inisery",
            "iniss",
            "inix",
            "injnry",
            "injurv",
            "inodel",
            "inodern",
            "inodest",
            "inodule",
            "inoney",
            "inonth",
            "inoon",
            "inoral",
            "inore",
            "inost",
            "inother",
            "inotion",
            "inotor",
            "inouse",
            "inouth",
            "inove",
            "insidc",
            "insnlt",
            "insnre",
            "instrurnent",
            "insurc",
            "intcnd",
            "intemal",
            "intemational",
            "inuch",
            "inud",
            "inurder",
            "inusic",
            "inust",
            "investrnent",
            "invitc",
            "iny",
            "inyself",
            "irnage",
            "irnaginary",
            "irnaginative",
            "irnagine",
            "irnitate",
            "irnitation",
            "irnpact",
            "irnplication",
            "irnply",
            "irnportance",
            "irnportant",
            "irnpose",
            "irnpossible",
            "irnpression",
            "irnprove",
            "irnprovernent",
            "irou",
            "islaud",
            "issne",
            "issuc",
            "itcm",
            "itein",
            "itern",
            "itsclf",
            "iu",
            "iu",
            "Iu",
            "iuch",
            "iucome",
            "iudeed",
            "iudex",
            "iudoor",
            "iuform",
            "iujury",
            "iuk",
            "iuside",
            "iusist",
            "iusult",
            "iusure",
            "iuteud",
            "Iuto",
            "iuto",
            "iuu",
            "iuveut",
            "iuvite",
            "iuward",
            "jndge",
            "jnmp",
            "Jnst",
            "jnst",
            "jobn",
            "joh",
            "joiu",
            "joiut",
            "jom",
            "jomt",
            "joumey",
            "jov",
            "judgc",
            "juinp",
            "jurnp",
            "Kack",
            "kccp",
            "Kccp",
            "Kcep",
            "kcy",
            "Ke",
            "Kecause",
            "Kecp",
            "Kefore",
            "Ketween",
            "kev",
            "kingdorn",
            "kiud",
            "kiug",
            "kmd",
            "kmg",
            "kncc",
            "knccl",
            "knifc",
            "Kome",
            "kuee",
            "kueel",
            "kuife",
            "kuock",
            "kuot",
            "Kuow",
            "kuow",
            "Kut",
            "Kven",
            "l0th",
            "l1ad",
            "l1th",
            "l2th",
            "l3th",
            "l4th",
            "l5th",
            "l6th",
            "l7th",
            "l8th",
            "l9th",
            "labonr",
            "ladv",
            "lahour",
            "lainp",
            "lakc",
            "langh",
            "lannch",
            "largc",
            "larnp",
            "latc",
            "latcly",
            "latcr",
            "latelv",
            "lattcr",
            "laugb",
            "launcb",
            "lauuch",
            "lav",
            "lawver",
            "lawycr",
            "lazv",
            "lcad",
            "lcadcr",
            "lcaf",
            "lcaguc",
            "lcan",
            "lcarn",
            "lcast",
            "lcavc",
            "lcft",
            "lcg",
            "lcgal",
            "lcnd",
            "lcngth",
            "lcss",
            "lcsscn",
            "lcsson",
            "lcttcr",
            "lcvcl",
            "leagne",
            "leam",
            "learu",
            "leau",
            "lengtb",
            "lengtli",
            "lesseu",
            "lessou",
            "leud",
            "leugth",
            "lgth",
            "liabit",
            "liair",
            "lialf",
            "liall",
            "liand",
            "liandle",
            "liang",
            "liappen",
            "liappy",
            "liarbor",
            "liard",
            "liarden",
            "liardly",
            "liarm",
            "lias",
            "liaste",
            "liasten",
            "liat",
            "liate",
            "liatred",
            "liave",
            "lic",
            "licll",
            "liead",
            "lieal",
            "lieap",
            "liear",
            "lieart",
            "lieat",
            "lieaven",
            "lieavy",
            "liell",
            "liello",
            "lielp",
            "lience",
            "liere",
            "lifc",
            "ligbt",
            "liglit",
            "liide",
            "liigli",
            "liill",
            "liim",
            "liinb",
            "liinder",
            "liinit",
            "liire",
            "liis",
            "liit",
            "Likc",
            "likc",
            "likcly",
            "likelv",
            "limh",
            "linc",
            "liold",
            "liole",
            "liollow",
            "lioly",
            "liome",
            "lionest",
            "lionor",
            "liook",
            "liope",
            "liorse",
            "liost",
            "liot",
            "liotel",
            "liour",
            "liouse",
            "liow",
            "liqnid",
            "lirnb",
            "lirnit",
            "lirnited",
            "listcn",
            "listeu",
            "littie",
            "Littlc",
            "littlc",
            "liue",
            "liuge",
            "liuk",
            "liumble",
            "liunger",
            "liunt",
            "liurry",
            "liurt",
            "liut",
            "livc",
            "liviug",
            "livmg",
            "lIy",
            "llth",
            "lme",
            "lmk",
            "lnck",
            "lnmp",
            "lnnch",
            "lnng",
            "loau",
            "localitv",
            "lodgc",
            "loncly",
            "lond",
            "lonelv",
            "loosc",
            "looscn",
            "looseu",
            "losc",
            "louely",
            "loug",
            "Loug",
            "loval",
            "lovc",
            "lovcly",
            "lovelv",
            "lst",
            "ltim",
            "luinp",
            "luncb",
            "luncli",
            "lurnp",
            "luuch",
            "luug",
            "maiiaged",
            "mainlv",
            "maiu",
            "maiuly",
            "makc",
            "Makc",
            "malc",
            "mamly",
            "managc",
            "managernent",
            "manncr",
            "manv",
            "Manv",
            "marcb",
            "marcli",
            "markct",
            "marrv",
            "mastcr",
            "matcb",
            "matcli",
            "mattcr",
            "mau",
            "mauage",
            "mauuer",
            "mauy",
            "Mauy",
            "mav",
            "Mav",
            "mavbe",
            "maybc",
            "mayhe",
            "mb  ",
            "mbber",
            "mc",
            "mcal",
            "mcan",
            "mcans",
            "mcat",
            "mcct",
            "mch",
            "mclt",
            "mcmbcr",
            "mcmory",
            "mcnd",
            "mcntal",
            "mcome",
            "mcrc",
            "mcrcly",
            "mcrcy",
            "mcrry",
            "mctal",
            "mcthod",
            "mde",
            "mdeed",
            "mdex",
            "mdoor",
            "meantirne",
            "meanwbile",
            "meau",
            "meaus",
            "memher",
            "memhers",
            "memorv",
            "mercv",
            "merelv",
            "mernber",
            "mernbership",
            "mernory",
            "merrv",
            "metbod",
            "metliod",
            "meud",
            "meutal",
            "mform",
            "middlc",
            "Migbt",
            "migbt",
            "miglit",
            "Miglit",
            "milc",
            "minc",
            "minnte",
            "minutc",
            "miscry",
            "miserv",
            "miud",
            "miue",
            "miuute",
            "mjury",
            "mk",
            "mle",
            "mmd",
            "mme",
            "mmute",
            "mn",
            "mn",
            "Mncb",
            "mnch",
            "Mnch",
            "mnd",
            "mnrder",
            "mnsenm",
            "mnsic",
            "mnst",
            "modcl",
            "modcrn",
            "modcst",
            "modem",
            "moderu",
            "modnle",
            "modulc",
            "momcnt",
            "momeut",
            "moming",
            "moncy",
            "monev",
            "monkev",
            "monse",
            "montb",
            "montli",
            "moou",
            "Morc",
            "morc",
            "mornent",
            "mornentary",
            "motber",
            "mothcr",
            "motiou",
            "motlier",
            "mouey",
            "mousc",
            "moutb",
            "moutli",
            "Movc",
            "movc",
            "movernent",
            "mral",
            "msect",
            "msh",
            "mside",
            "msist",
            "mst",
            "msult",
            "msure",
            "mtend",
            "mto",
            "Mucb",
            "mucb",
            "Mucli",
            "mucli",
            "murdcr",
            "museurn",
            "mv",
            "mvite",
            "mvself",
            "mward",
            "mysclf",
            "naine",
            "namc",
            "narne",
            "nativc",
            "natnre",
            "naturc",
            "nc",
            "ncar",
            "ncarly",
            "ncat",
            "nccd",
            "ncck",
            "ncphcw",
            "ncst",
            "nct",
            "Ncvcr",
            "ncvcr",
            "Ncver",
            "ncw",
            "ncws",
            "ncxt",
            "nearlv",
            "neitber",
            "ner",
            "nepbew",
            "Nevcr",
            "ngly",
            "nian",
            "nicc",
            "niccc",
            "nigbt",
            "niglit",
            "nlyself",
            "nnable",
            "nncle",
            "nnder",
            "nnion",
            "nnit",
            "nnite",
            "nnited",
            "nnity",
            "nnless",
            "nnmber",
            "nnrse",
            "nnt",
            "nntil",
            "noblc",
            "nobodv",
            "nohle",
            "nohody",
            "noisc",
            "nonc",
            "norinal",
            "norrnal",
            "norrnally",
            "nortb",
            "nortbern",
            "northem",
            "nortli",
            "nosc",
            "notbing",
            "notc",
            "noticc",
            "np",
            "npon",
            "npper",
            "npset",
            "nrge",
            "nrgent",
            "ns",
            "nse",
            "nsed",
            "nsefnl",
            "nser",
            "nsnal",
            "Nte",
            "nuinber",
            "numbcr",
            "numher",
            "numhers",
            "nurnber",
            "nurnerous",
            "nursc",
            "oan",
            "obcy",
            "obev",
            "objcct",
            "obtaiu",
            "obtam",
            "occan",
            "occnr",
            "oceau",
            "offcnd",
            "offcr",
            "offeud",
            "officc",
            "oftcn",
            "ofteu",
            "ohey",
            "ohject",
            "ohtain",
            "oinit",
            "okav",
            "om",
            "omament",
            "Onc",
            "onc",
            "Oncc",
            "oncc",
            "onght",
            "oniy",
            "Onlv",
            "onlv",
            "onnce",
            "onr",
            "ont",
            "Ont",
            "ontpnt",
            "opcn",
            "Opcn",
            "Opeu",
            "opeu",
            "opposc",
            "optiou",
            "ordcr",
            "orgau",
            "origiu",
            "origm",
            "ornarnent",
            "ornission",
            "ornit",
            "Otber",
            "otber",
            "otbers",
            "othcr",
            "Othcr",
            "otlier",
            "Otlier",
            "Oucc",
            "Ouce",
            "ouce",
            "Oue",
            "oue",
            "ougbt",
            "ouglit",
            "Oulv",
            "ouly",
            "Ouly",
            "ouncc",
            "outcorne",
            "outo",
            "ouuce",
            "ovcr",
            "Ovcr",
            "overcorne",
            "owc",
            "owncr",
            "owu",
            "owuer",
            "pagc",
            "paiu",
            "paiut",
            "palc",
            "pamt",
            "pancl",
            "panse",
            "papcr",
            "parccl",
            "parcnt",
            "pardou",
            "pareut",
            "parliarnent",
            "partlv",
            "partv",
            "pastc",
            "pastrv",
            "patb",
            "patli",
            "pattem",
            "pau",
            "pauel",
            "pausc",
            "pav",
            "payrnent",
            "pbase",
            "pbone",
            "pcacc",
            "pcarl",
            "pcn",
            "pcncil",
            "pcnny",
            "Pcoplc",
            "pcoplc",
            "Pcople",
            "pcr",
            "pcriod",
            "pcrmit",
            "pcrson",
            "pct",
            "pennv",
            "Peoplc",
            "perbaps",
            "perforrn",
            "perforrnance",
            "perinit",
            "perrnanent",
            "perrnission",
            "perrnit",
            "persou",
            "peu",
            "peucil",
            "peuuy",
            "phasc",
            "phonc",
            "pia",
            "piccc",
            "pigcon",
            "pilc",
            "pincb",
            "pincli",
            "pipc",
            "pitv",
            "piu",
            "piuch",
            "piuk",
            "piut",
            "placc",
            "plaiu",
            "plam",
            "platc",
            "plau",
            "plaut",
            "plav",
            "plaver",
            "playcr",
            "plcasc",
            "plcnty",
            "plentv",
            "pleuty",
            "pliase",
            "plnral",
            "plns",
            "pmch",
            "pmk",
            "pmt",
            "pnb",
            "pnblic",
            "pnll",
            "pnmp",
            "pnnish",
            "pnpil",
            "pnre",
            "pnrple",
            "pnsh",
            "pnt",
            "Pnt",
            "pnzzle",
            "pockct",
            "pocm",
            "poct",
            "poein",
            "poern",
            "pohte",
            "poisou",
            "poiut",
            "policc",
            "policv",
            "polisb",
            "politc",
            "pomt",
            "ponnd",
            "ponr",
            "pouud",
            "powcr",
            "powdcr",
            "praisc",
            "prav",
            "prcach",
            "prcfcr",
            "prcss",
            "prctty",
            "preacb",
            "preacli",
            "prettv",
            "pricc",
            "pricst",
            "pridc",
            "priine",
            "primc",
            "prirnary",
            "prirne",
            "prisou",
            "priut",
            "prizc",
            "prmt",
            "problern",
            "prohlem",
            "prohlems",
            "proinpt",
            "prond",
            "propcr",
            "prornise",
            "prornised",
            "prornote",
            "prornpt",
            "provc",
            "pubhc",
            "puh",
            "puhlic",
            "puinp",
            "punisb",
            "punisli",
            "purc",
            "purnp",
            "purplc",
            "pusb",
            "pusli",
            "puuish",
            "qnart",
            "qneen",
            "qnick",
            "qniet",
            "qnite",
            "qttict",
            "Quc",
            "quc",
            "quccn",
            "queeu",
            "quict",
            "quitc",
            "racc",
            "rahhit",
            "raisc",
            "raiu",
            "rangc",
            "rarc",
            "Rarly",
            "ratber",
            "ratc",
            "rathcr",
            "ratlier",
            "rauge",
            "rauk",
            "rav",
            "rcach",
            "rcad",
            "rcadcr",
            "rcady",
            "rcal",
            "rcally",
            "rcason",
            "rccall",
            "rcccnt",
            "rccord",
            "rcd",
            "rcddcn",
            "rcducc",
            "rcfcr",
            "rcform",
            "rcfusc",
            "rcgard",
            "rcgion",
            "rcgrct",
            "rcjcct",
            "rclatc",
            "rclicf",
            "rcly",
            "rcmain",
            "rcmark",
            "rcmcdy",
            "rcmind",
            "rcmovc",
            "rcnt",
            "rcpair",
            "rcpcat",
            "rcply",
            "rcport",
            "rcscuc",
            "rcsign",
            "rcsist",
            "rcst",
            "rcsult",
            "rctain",
            "rctirc",
            "rcturn",
            "rcvcal",
            "rcvicw",
            "rcward",
            "reacb",
            "reacli",
            "readv",
            "reallv",
            "reasou",
            "Recause",
            "receut",
            "reddeu",
            "rednce",
            "Reep",
            "refnse",
            "Refore",
            "reforin",
            "reforrn",
            "regiou",
            "rehef",
            "reinain",
            "reinark",
            "reinedy",
            "reinind",
            "reinove",
            "relv",
            "remaiu",
            "remam",
            "remcrnbered",
            "remedv",
            "remiud",
            "remmd",
            "renlincled",
            "replv",
            "requirernent",
            "rernain",
            "rernark",
            "rernedy",
            "rernernber",
            "rernind",
            "rernove",
            "rescne",
            "resigu",
            "resnlt",
            "retaiu",
            "retam",
            "retnrn",
            "retum",
            "returu",
            "Retween",
            "reut",
            "ribbou",
            "ricb",
            "ricc",
            "ricli",
            "ridc",
            "Rigbt",
            "rigbt",
            "riglit",
            "Riglit",
            "rihhon",
            "ripc",
            "ripcn",
            "ripeu",
            "risc",
            "riug",
            "rivcr",
            "rmg",
            "rnachine",
            "rnachinery",
            "rnad",
            "rnadden",
            "rnagazine",
            "rnail",
            "rnain",
            "rnainly",
            "rnaintain",
            "rnajor",
            "rnajority",
            "rnake",
            "rnale",
            "rnan",
            "rnanage",
            "rnanaged",
            "rnanagement",
            "rnanager",
            "rnankind",
            "rnanner",
            "rnany",
            "rnap",
            "rnarch",
            "rnark",
            "rnarket",
            "rnarriage",
            "rnarried",
            "rnarry",
            "rnass",
            "rnaster",
            "rnat",
            "rnatch",
            "rnaterial",
            "rnatter",
            "rnay",
            "rnaybe",
            "rnb",
            "rnbber",
            "rnde",
            "rne",
            "rneal",
            "rnean",
            "rneaning",
            "rneans",
            "rneantirne",
            "rneanwhile",
            "rneasure",
            "rneat",
            "rnechanisrn",
            "rnedical",
            "rnedicine",
            "rneet",
            "rneeting",
            "rnelt",
            "rnember",
            "rnembership",
            "rnemory",
            "rnend",
            "rnental",
            "rnention",
            "rnerchant",
            "rnercy",
            "rnere",
            "rnerely",
            "rnerry",
            "rnessage",
            "rnessenger",
            "rnetal",
            "rnethod",
            "rng",
            "rniddle",
            "rnight",
            "rnild",
            "rnile",
            "rnilitary",
            "rnilk",
            "rnill",
            "rnin",
            "rnind",
            "rnine",
            "rnineral",
            "rninister",
            "rninistry",
            "rninute",
            "rninutes",
            "rniserable",
            "rnisery",
            "rniss",
            "rnistake",
            "rnix",
            "rnixture",
            "rnle",
            "rnn",
            "rnodel",
            "rnoderate",
            "rnoderation",
            "rnodern",
            "rnodest",
            "rnodesty",
            "rnodule",
            "rnoney",
            "rnonkey",
            "rnonth",
            "rnoon",
            "rnoonlight",
            "rnoral",
            "rnore",
            "rnoreover",
            "rnornent",
            "rnornentary",
            "rnorning",
            "rnost",
            "rnother",
            "rnotherhood",
            "rnotherly",
            "rnotion",
            "rnountain",
            "rnouse",
            "rnouth",
            "rnove",
            "rnovement",
            "Rnow",
            "rnral",
            "rnsh",
            "rnst",
            "rnuch",
            "rnud",
            "rnultiply",
            "rnurder",
            "rnuseurn",
            "rnusic",
            "rnusician",
            "rnust",
            "rny",
            "rnyself",
            "rnystery",
            "roh",
            "rolc",
            "rongh",
            "ronnd",
            "ronte",
            "rooin",
            "roorn",
            "ropc",
            "rottcn",
            "rotteu",
            "rougb",
            "rougli",
            "routc",
            "rouud",
            "roval",
            "rubbcr",
            "rudc",
            "ruh",
            "ruhher",
            "ruiu",
            "rulc",
            "rusb",
            "rusli",
            "ruu",
            "Rven",
            "Ry",
            "sacrcd",
            "saddcn",
            "saddeu",
            "saddlc",
            "safc",
            "safcty",
            "safetv",
            "saine",
            "sainple",
            "sakc",
            "salarv",
            "salc",
            "salesrnan",
            "samc",
            "samplc",
            "sance",
            "sancer",
            "sarne",
            "sarnple",
            "saucc",
            "sauccr",
            "saud",
            "sav",
            "savc",
            "sbade",
            "sbadow",
            "sbake",
            "sball",
            "sbame",
            "sbape",
            "sbare",
            "sbarp",
            "sbave",
            "Sbc",
            "Sbe",
            "sbe",
            "sbeep",
            "sbeet",
            "sbelf",
            "sbell",
            "sbield",
            "sbine",
            "sbip",
            "sbirt",
            "sbock",
            "sboe",
            "Sbonld",
            "sboot",
            "sbop",
            "sbore",
            "sbort",
            "sbot",
            "Sbould",
            "sbould",
            "sbout",
            "Sbow",
            "sbow",
            "sbower",
            "sbut",
            "sca",
            "scalc",
            "scarcc",
            "scarch",
            "scason",
            "scbeme",
            "scbool",
            "scbools",
            "scc",
            "Scc",
            "sccd",
            "scck",
            "sccm",
            "sccnc",
            "sccnt",
            "sccond",
            "sccrct",
            "sccurc",
            "Sce",
            "sceue",
            "sceut",
            "schcmc",
            "scheine",
            "scherne",
            "scizc",
            "sclcct",
            "scldom",
            "sclf",
            "scliool",
            "scll",
            "scnd",
            "scnior",
            "scnsc",
            "scom",
            "scorc",
            "scoru",
            "scrapc",
            "scrccn",
            "scrcw",
            "screeu",
            "scrics",
            "scrvc",
            "sct",
            "Sct",
            "scttlc",
            "scvcrc",
            "scw",
            "searcb",
            "searcli",
            "seasou",
            "secnre",
            "secoud",
            "seein",
            "seern",
            "seldoin",
            "seldorn",
            "settlernent",
            "seud",
            "seuior",
            "seuse",
            "shadc",
            "shaine",
            "shakc",
            "shamc",
            "shapc",
            "sharc",
            "sharne",
            "shavc",
            "shc",
            "Shc",
            "shcct",
            "shclf",
            "shcll",
            "shde",
            "shght",
            "shicld",
            "shinc",
            "shiue",
            "shme",
            "shnt",
            "shoc",
            "shonld",
            "Shonld",
            "shont",
            "shorc",
            "shouldnt",
            "showcr",
            "sidc",
            "sigbt",
            "siglit",
            "sigu",
            "sigual",
            "siinple",
            "siinply",
            "silcnt",
            "sileut",
            "silvcr",
            "simplc",
            "simplv",
            "sinall",
            "Sinall",
            "sincc",
            "Sincc",
            "sinell",
            "singlc",
            "sinile",
            "sinoke",
            "sinooth",
            "sirnilar",
            "sirnple",
            "sirnplicity",
            "sirnply",
            "sistcr",
            "sitc",
            "siuce",
            "Siuce",
            "siug",
            "siugle",
            "siuk",
            "sizc",
            "skiu",
            "skm",
            "skv",
            "slavc",
            "slccp",
            "sliade",
            "sliake",
            "sliall",
            "sliame",
            "sliape",
            "sliare",
            "sliarp",
            "slidc",
            "Slie",
            "slie",
            "slieet",
            "slielf",
            "sliell",
            "sligbt",
            "sliglit",
            "sliield",
            "sliine",
            "sliip",
            "sliirt",
            "slioe",
            "Slionld",
            "slioot",
            "sliop",
            "sliore",
            "sliort",
            "sliot",
            "Sliould",
            "sliould",
            "sliout",
            "Sliow",
            "sliow",
            "sliut",
            "slopc",
            "slowlv",
            "Smce",
            "smce",
            "smcll",
            "smg",
            "smgle",
            "smilc",
            "smk",
            "smokc",
            "smootb",
            "smootli",
            "snakc",
            "snch",
            "Snch",
            "sndden",
            "snffer",
            "sngar",
            "snit",
            "snm",
            "snmmer",
            "snn",
            "snpper",
            "snpply",
            "snre",
            "snrely",
            "snrvey",
            "softcn",
            "softeu",
            "sohd",
            "Soine",
            "soine",
            "solcmn",
            "soleinn",
            "solemu",
            "solernn",
            "solvc",
            "somc",
            "Somc",
            "somcthing",
            "sometbing",
            "sonl",
            "sonnd",
            "sonp",
            "sonr",
            "sonrce",
            "sonth",
            "soou",
            "sorc",
            "Sorne",
            "sorne",
            "sornebody",
            "sornehow",
            "sorneone",
            "sornething",
            "sornetirne",
            "sornetirnes",
            "sornewhat",
            "sornewhere",
            "sorrv",
            "sou",
            "soug",
            "sourcc",
            "soutb",
            "southem",
            "soutli",
            "souud",
            "spacc",
            "spadc",
            "sparc",
            "spcak",
            "spccch",
            "spccd",
            "spcll",
            "spcnd",
            "speecb",
            "speecli",
            "speud",
            "spht",
            "spitc",
            "spiu",
            "spm",
            "spoou",
            "sprcad",
            "spriug",
            "sprmg",
            "sqnare",
            "squarc",
            "Srnall",
            "srnall",
            "srnell",
            "srnile",
            "srnoke",
            "srnooth",
            "stagc",
            "stainp",
            "staiu",
            "starnp",
            "statc",
            "staternent",
            "statns",
            "staud",
            "Staud",
            "stav",
            "stcady",
            "stcal",
            "stcam",
            "stccl",
            "stccp",
            "stccr",
            "stcm",
            "stcp",
            "steadv",
            "steain",
            "stearn",
            "stiug",
            "stmg",
            "stndio",
            "stndy",
            "stnff",
            "stnpid",
            "stonc",
            "storc",
            "storin",
            "stornach",
            "storrn",
            "storv",
            "stoue",
            "stovc",
            "strcam",
            "strcct",
            "streain",
            "strearn",
            "strikc",
            "stripc",
            "striug",
            "strmg",
            "strokc",
            "stroug",
            "studv",
            "stvle",
            "stylc",
            "suake",
            "sucb",
            "Sucb",
            "Sucli",
            "sucli",
            "suddcn",
            "suddeu",
            "suffcr",
            "suin",
            "summcr",
            "suow",
            "suppcr",
            "supplv",
            "surc",
            "surcly",
            "surelv",
            "surn",
            "surnrner",
            "survcy",
            "survev",
            "suu",
            "svstem",
            "swcar",
            "swcat",
            "swccp",
            "swcct",
            "swcll",
            "swiin",
            "swirn",
            "switcb",
            "switcli",
            "swiug",
            "swmg",
            "syrnpathetic",
            "syrnpathy",
            "systcm",
            "systein",
            "systern",
            "t11e",
            "tablc",
            "tahle",
            "taine",
            "Takc",
            "takc",
            "tamc",
            "tapc",
            "targct",
            "tarne",
            "tastc",
            "tban",
            "tbank",
            "tbanks",
            "tbat",
            "Tbat",
            "Tbcre",
            "Tbe",
            "tbe",
            "tbe",
            "tbeir",
            "tbem",
            "tbeme",
            "tben",
            "Tben",
            "tbeory",
            "Tberc",
            "Tbere",
            "tbere",
            "Tbese",
            "tbese",
            "tbey",
            "Tbey",
            "tbick",
            "tbief",
            "tbin",
            "tbing",
            "tbink",
            "tbirst",
            "Tbis",
            "tbis",
            "tborn",
            "Tbose",
            "tbose",
            "tbougb",
            "tbread",
            "tbreat",
            "tbroat",
            "Tbrougb",
            "Tbrough",
            "tbrow",
            "tbumb",
            "tbus",
            "tca",
            "tcach",
            "tcam",
            "tcar",
            "tcaring",
            "tcll",
            "tcmpcr",
            "tcmplc",
            "tcmpt",
            "tcnd",
            "tcndcr",
            "tcnding",
            "tcnt",
            "tcrm",
            "tcrms",
            "tcst",
            "tcxt",
            "teacb",
            "teacli",
            "teain",
            "tearn",
            "teh",
            "teinper",
            "teinple",
            "teinpt",
            "terin",
            "terins",
            "ternper",
            "ternperature",
            "ternple",
            "ternpt",
            "terrn",
            "terrns",
            "teud",
            "teuder",
            "teut",
            "thau",
            "thauk",
            "thauks",
            "thc",
            "thcir",
            "thcm",
            "thcmc",
            "thcn",
            "Thcn",
            "thcory",
            "thcrc",
            "Thcrc",
            "Thcre",
            "thcsc",
            "Thcy",
            "thcy",
            "thein",
            "theine",
            "theorv",
            "Therc",
            "thern",
            "therne",
            "thernselves",
            "Thesc",
            "theu",
            "Thev",
            "thev",
            "theyll",
            "thicf",
            "thiu",
            "thiug",
            "thiuk",
            "thm",
            "thmg",
            "thmk",
            "thnmb",
            "thns",
            "thom",
            "thongh",
            "thosc",
            "Thosc",
            "thougb",
            "thrcad",
            "thrcat",
            "Throngh",
            "Througb",
            "thuinb",
            "thumh",
            "thurnb",
            "tickct",
            "tidc",
            "tidv",
            "tigbt",
            "tiglit",
            "tiine",
            "timc",
            "timne",
            "tinv",
            "tirc",
            "tirne",
            "titlc",
            "tiu",
            "tiuy",
            "tlian",
            "tliank",
            "tlianks",
            "Tliat",
            "tliat",
            "Tlie",
            "tlie",
            "tlieir",
            "tliem",
            "tlien",
            "Tlien",
            "Tliere",
            "tliere",
            "tliese",
            "Tliese",
            "Tliey",
            "tliey",
            "tliick",
            "tliief",
            "tliin",
            "tliing",
            "tliink",
            "tliirst",
            "Tliis",
            "tliis",
            "tliose",
            "Tliose",
            "tliread",
            "tlireat",
            "tlirow",
            "tlius",
            "Tm",
            "tmy",
            "tnbe",
            "tnne",
            "Tnrn",
            "tnrn",
            "toc",
            "todav",
            "togetber",
            "tonc",
            "tonch",
            "tongh",
            "tongne",
            "tonguc",
            "tonr",
            "tootb",
            "Torn",
            "tornorrow",
            "tou",
            "toucb",
            "toucli",
            "toue",
            "tougb",
            "tougli",
            "tougue",
            "tov",
            "towcl",
            "towcr",
            "towu",
            "toxvard",
            "tradc",
            "traiu",
            "trav",
            "travcl",
            "trcat",
            "trcaty",
            "trcc",
            "trcnd",
            "treatrnent",
            "treatv",
            "trernble",
            "treud",
            "tribc",
            "trihe",
            "trne",
            "trnnk",
            "trnst",
            "trnth",
            "truc",
            "trutb",
            "trutli",
            "truuk",
            "trv",
            "tubc",
            "tuhe",
            "tumpike",
            "tunc",
            "turu",
            "Turu",
            "tuue",
            "tvpe",
            "twicc",
            "typc",
            "uail",
            "uame",
            "uarrow",
            "uatiou",
            "uative",
            "uature",
            "uear",
            "uearly",
            "ueat",
            "ueck",
            "ueed",
            "ueedle",
            "uephew",
            "uest",
            "uet",
            "uever",
            "uew",
            "uews",
            "uext",
            "uglv",
            "uice",
            "uiece",
            "uight",
            "unablc",
            "unahle",
            "unc",
            "unclc",
            "undcr",
            "Undcr",
            "undemeath",
            "unitc",
            "unitcd",
            "unitv",
            "unlcss",
            "uoble",
            "uobody",
            "uod",
            "uoise",
            "uoou",
            "uor",
            "uormal",
            "uorth",
            "uose",
            "uot",
            "uote",
            "uotice",
            "uotiou",
            "uoue",
            "uow",
            "upou",
            "uppcr",
            "upperrnost",
            "upsct",
            "urgc",
            "urgcnt",
            "urgeut",
            "Usc",
            "usc",
            "uscd",
            "uscful",
            "uscr",
            "uuable",
            "uucle",
            "uuder",
            "uuiou",
            "uuit",
            "uuite",
            "uuited",
            "uuity",
            "uuless",
            "uumber",
            "uurse",
            "uut",
            "uutil",
            "vaiu",
            "vallcy",
            "vallev",
            "valne",
            "valuc",
            "vam",
            "vard",
            "varv",
            "vcil",
            "vcrb",
            "vcrsc",
            "vcry",
            "Vcry",
            "vcsscl",
            "veah",
            "vear",
            "vellow",
            "verv",
            "Verv",
            "ves",
            "vho",
            "victiin",
            "victirn",
            "vicw",
            "vield",
            "virtne",
            "virtuc",
            "visiou",
            "voicc",
            "volnme",
            "voluine",
            "volumc",
            "volurne",
            "votc",
            "vou",
            "voung",
            "vour",
            "vouth",
            "vovage",
            "vowcl",
            "voyagc",
            "waa",
            "wagc",
            "waiking",
            "waitcr",
            "wakc",
            "wam",
            "wandcr",
            "warinth",
            "warmtb",
            "warmtli",
            "warrn",
            "warrnth",
            "waru",
            "wasb",
            "wasli",
            "wasnt",
            "wastc",
            "watcb",
            "watcli",
            "watcr",
            "wauder",
            "waut",
            "wav",
            "wavc",
            "wbat",
            "Wbat",
            "wbeat",
            "wbeel",
            "wben",
            "Wben",
            "Wbere",
            "wbere",
            "Wbeu",
            "wbich",
            "wbile",
            "Wbile",
            "wbilst",
            "wbip",
            "wbite",
            "wbo",
            "Wbo",
            "wbole",
            "wbom",
            "wbose",
            "wby",
            "Wc",
            "wc",
            "wcak",
            "wcakcn",
            "wcalth",
            "wcapon",
            "wcar",
            "wcavc",
            "wccd",
            "wcck",
            "wcigh",
            "wcight",
            "wcll",
            "wcst",
            "wct",
            "weakeu",
            "wealtb",
            "weapou",
            "weigb",
            "weigbt",
            "welcorne",
            "westem",
            "whcat",
            "whccl",
            "whcn",
            "Whcn",
            "Whcrc",
            "whcrc",
            "Whcre",
            "Wherc",
            "wheu",
            "Wheu",
            "whicb",
            "Whicb",
            "Whicb",
            "whicli",
            "whilc",
            "Whilc",
            "whitc",
            "whitcn",
            "whiteu",
            "whoin",
            "wholc",
            "whorn",
            "whosc",
            "whv",
            "wickcd",
            "widc",
            "widcly",
            "widcn",
            "widelv",
            "wideu",
            "widtb",
            "widtli",
            "wifc",
            "winc",
            "winncr",
            "wintcr",
            "wipc",
            "wirc",
            "wisb",
            "wisc",
            "wisdoin",
            "wisdorn",
            "wisli",
            "Witb",
            "witb",
            "witbin",
            "witbout",
            "withiu",
            "withm",
            "witli",
            "Witli",
            "witliin",
            "wiu",
            "wiud",
            "wiudow",
            "wiue",
            "wiug",
            "wiuter",
            "wiuuer",
            "Wliat",
            "wliat",
            "wlien",
            "Wlien",
            "Wliere",
            "wliere",
            "wliich",
            "Wliile",
            "wliile",
            "wliilst",
            "wliip",
            "wliite",
            "Wlio",
            "wlio",
            "wliole",
            "wliom",
            "wliose",
            "wliy",
            "wmd",
            "wmdow",
            "wme",
            "wmg",
            "wmner",
            "wmter",
            "wo",
            "woinan",
            "womau",
            "wondcr",
            "wonld",
            "wonnd",
            "woodcn",
            "woodeu",
            "woolcn",
            "wooleu",
            "worin",
            "workcr",
            "wornan",
            "worrn",
            "worrv",
            "worsc",
            "wortb",
            "wortli",
            "wouder",
            "wouid",
            "wouldnt",
            "wouud",
            "wrcck",
            "writc",
            "writcr",
            "wroug",
            "ycar",
            "ycllow",
            "ycs",
            "yct",
            "yicld",
            "yntir",
            "yonng",
            "yonr",
            "yonth",
            "youtb",
            "youtli",
            "youug",
            "youve",
            "zcro",
            "stiil",
            "aword",
            "nnd",
            "KEW",
            "Sonth",
            "wa",
            "ou",
            "aa",
            "klnd",
            "tne",
            "ths",
        ]

        scanno_dictionary = {}

        for scoword in scannos_misspelled:
            if scoword in scanno_dictionary:
                continue
            scanno_dictionary[scoword] = 0
            wl = scoword.lower()
            wt = wl.title()
            if wt != scoword:
                scanno_dictionary[wt] = 0
            wu = wl.upper()
            if wu != scoword:
                scanno_dictionary[wu] = 0
        return scanno_dictionary

    def mask_special_cases(match_obj):
        if match_obj.group(2) == "-":
            repl = "①"
        elif match_obj.group(2) == "’":
            repl = "②"
        elif match_obj.group(2) == "‘":
            repl = "③"
        elif match_obj.group(2) == "'":
            repl = "④"
        elif match_obj.group(2) == ".":
            repl = "⑤"
        elif match_obj.group(2) == "^":
            repl = "⑥"
        elif match_obj.group(2) == "—":
            # Replace emdash with space in this situation
            repl = " "
        else:
            repl = match_obj.group(2)
        return match_obj.group(1) + repl + match_obj.group(3)

    def get_words_on_line(line):
        # Parses the text to find all the words on a line
        # and returns them as a (possibly empty) list.

        if len(line) == 0:
            return []

        # Words may be surrounded by abandoned HTML tags, entities,
        # Unicode numeric character references, etc. Remove these
        # from the line first of all so genuine words are easier to
        # identify.

        # A document starting with a "<!DOCTYPE>" declaration is
        # assumed to be an HTML file and is rejected by the main
        # program, so we should never get here and encounter such
        # a declaration on a line. Just in case, however, we look
        # out for it as we look out for abandoned HTML tags. But
        # we have to treat this HTML declaration specially as it
        # may overflow onto a second line. Check for this.

        nonlocal long_doctype_decl

        re_doctype = re.compile(r"(?i)<!DOCTYPE")

        if long_doctype_decl:
            # Second line of a long <!DOCTYPE> declaration. Toss it.
            long_doctype_decl = False
            return []

        if re_doctype.search(line) and ">" not in line:
            # Looks like a two-line <!DOCTYPE declaration. Toss it
            # and set flag to toss the second line too.
            long_doctype_decl = True
            return []

        # A short HTML 5 <!DOCTYPE> declaration will not be detected
        # by the above tests. However it will be detected as an HTML
        # 'tag' next and removed from line.

        re_tag = re.compile(r"(?s)(<(?=[!\/a-z]).*?(?<=[\"A-Za-z0-9\/]|-)>)")
        new_line = ""
        while res := re_tag.search(line):
            new_line += " " + line[0 : res.start(0)]
            line = line[res.start(0) + len(res.group(0)) :]

        if len(line) != 0:
            new_line += " " + line
        line = new_line

        # Replace HTML entities (e.g. &amp;) with a space.
        re_entity = re.compile(r"(&[a-z0-9]+?;)")
        new_line = ""
        while res := re_entity.search(line):
            new_line += " " + line[0 : res.start(0)]
            line = line[res.start(0) + len(res.group(0)) :]

        if len(line) != 0:
            new_line += " " + line
        line = new_line

        # Replace Unicode numeric character references with a space.
        re_unicode = re.compile(r"(&#[0-9]{1,4};|&#x[0-9a-fA-F]{1,4};)")
        new_line = ""
        while res := re_unicode.search(line):
            new_line += " " + line[0 : res.start(0)]
            line = line[res.start(0) + len(res.group(0)) :]

        if len(line) != 0:
            new_line += " " + line
        line = new_line

        # Replace 1/2-style fractions with a space.
        re_frac = re.compile(r"[0-9]+?/[0-9]+?")
        new_line = ""
        while res := re_frac.search(line):
            new_line += " " + line[0 : res.start(0)]
            line = line[res.start(0) + len(res.group(0)) :]

        if len(line) != 0:
            new_line += " " + line
        line = new_line

        # Replace [99]-type footnote anchors with a space.
        re_fna = re.compile(r"\[[0-9]+?\]|\[[0-9]+?[a-zA-Z]\]")
        new_line = ""
        while res := re_fna.search(line):
            new_line += " " + line[0 : res.start(0)]
            line = line[res.start(0) + len(res.group(0)) :]

        if len(line) != 0:
            new_line += " " + line
        line = new_line

        # Remove italic markup (_) before letter and after letter or period (.).
        # re_italic = re.compile("(.*?)(_(?=\p{L})[\p{L}\.]*?(?<=\p{L}|\p{L}\.)_)(.*)")
        re_italic = re.compile(r"(.*?)(_(?=\p{L}).*?(?<=\p{L}|\.)_)(.*)")
        while res := re_italic.search(line):
            t = res.group(2)
            t = t.replace("_", " ")
            line = res.group(1) + t + res.group(3)

        # Protect special cases by masking them temporarily:
        # E.g.
        # high-flying, hasn’t, ’tis, Househ^d
        # all stay intact
        # Capitalisation is retained.
        # Additionally, an emdash separating words in, for
        # example, the ToC is replaced by a space.

        # Need these twice to handle alternates
        # E.g. fo’c’s’le

        # Emdash
        line = re.sub(
            r"([\p{L}\p{Nd}\p{P}=])(\—)([\p{L}\p{N}’‘“_\(])", mask_special_cases, line
        )
        line = re.sub(
            r"([\p{L}\p{Nd}\p{P}=])(\—)([\p{L}\p{N}’‘“_\(])", mask_special_cases, line
        )
        # Minus
        line = re.sub(r"([\p{L}①②③④⑤\.=])(\-)([\p{L}\p{N}])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤\.=])(\-)([\p{L}\p{N}])", mask_special_cases, line)
        # The others.
        line = re.sub(r"([\p{L}①②③④⑤])(’)([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤])(’)([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤]|^)(’)([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤]|^)(’)([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤])(‘)([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤])(‘)([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤])(\')([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤])(\')([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤]|^)(\')([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤]|^)(\')([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(
            r"([\p{L}①②③④⑤])(\.)([\p{L}①②③④⑤\p{P}])", mask_special_cases, line
        )
        line = re.sub(
            r"([\p{L}①②③④⑤])(\.)([\p{L}①②③④⑤\p{P}])", mask_special_cases, line
        )
        line = re.sub(
            r"([\p{L}①②③④⑤])(\^)([\p{L}①②③④⑤\p{P}])", mask_special_cases, line
        )
        line = re.sub(
            r"([\p{L}①②③④⑤])(\^)([\p{L}①②③④⑤\p{P}])", mask_special_cases, line
        )

        s = ""
        indx = 0

        while indx < len(line):
            # Look for 'words', one character at a time.
            if (
                line[indx : indx + 1].isnumeric()
                or line[indx : indx + 1].isalpha()
                or line[indx : indx + 1].isspace()
            ):
                s = s + line[indx : indx + 1]
            else:
                s = s + " "
            indx += 1

        # Use temporary list to hold the split line while we put
        # back the protected characters.
        T = s.split()
        L = []
        for n in range(len(T)):
            # For efficiency!
            Tn = T[n]
            Tn = Tn.replace("①", "-")
            Tn = Tn.replace("②", "’")
            Tn = Tn.replace("③", "‘")
            Tn = Tn.replace("④", "'")
            Tn = Tn.replace("⑤", ".")
            Tn = Tn.replace("⑥", "^")
            L.append(Tn)
        return L

    def scanno_check():
        print("scanno check", file=string_out)

        scanno_dictionary = build_scanno_dictionary()
        scanno_outrecs = {}
        no_scannos_found = True

        line_number = 1
        for line in book:
            # We have the list of words on the line already in
            # the array 'line_word_list'. It is indexed from
            # zero, not one.

            L = line_word_list[line_number - 1]

            for word in L:
                if word in scanno_dictionary:
                    no_scannos_found = False

                    # Add a record for the scanno to be output to the log later.
                    # Create the initial entry for this scanno if necessary.
                    if word not in scanno_outrecs:
                        scanno_outrecs[word] = []
                    scanno_outrecs[word].append(make_a_report_record(line_number, line))

            line_number += 1

        # We're done looking for scannos. Report what we found.
        # NB scanno_outrecs is a dictionary. The keys are a scanno
        #    and the value is a list of output records (line number,
        #    line) containing that scanno.

        for scanno in scanno_outrecs:
            # The scanno word is used as a header for all the lines
            # output to the report that contain the scanno.

            output_record = "\n" + scanno
            print(output_record, file=string_out)

            # Now process and output those records.

            rec_cnt = 0

            for output_record in scanno_outrecs[scanno]:
                # There may be more than one instance of the scanno on
                # the original line of text. Highlight each instance
                # in the output record (which contains a copy of 'line).

                slices_to_highlight = []
                indx = 0

                # We search successively shorter sections of the record.
                # ignoring the bit previously searched. The record to be
                # output will always contain at least one instance of the
                # scanno.

                while True:
                    # Make sure scanno is not found *within* a word.
                    # E.g. that scanno 'ou' is not found in 'you'.
                    pattern = "\\b" + scanno + "\\b"

                    if res := re.search(pattern, output_record[indx:]):
                        # Each 'slice' of output_record to highlight is
                        # defined as a tuple:
                        #   (start of slice in record, length of slice)
                        indx += res.start()
                        # Add the slice to our list.
                        slices_to_highlight.append((indx, len(scanno)))
                        indx += len(scanno)
                    else:
                        break

                # We have a list of slices of the ourput record to be
                # highlighted before printing to the report. The list
                # will always contain at least one slice.

                output_record = decorate(
                    output_record, slices_to_highlight, "redonyellow"
                )

                if verbose or rec_cnt < 2:
                    print(output_record, file=string_out)

                rec_cnt += 1

            if not verbose and rec_cnt > 2:
                # Tell user how many lines above 2 not printed.
                remaining = len(scanno_outrecs[scanno]) - 2
                print("    ...", remaining, "more", file=string_out)

        if no_scannos_found:
            print("\n    no scanno suspects found in text", file=string_out)

        template = "\n{}"
        print(template.format("-" * 80), file=string_out)

    def regex_search(word, record):
        # 'word' may contain '^' which needs to be escaped for regex search.
        word = word.replace("^", r"\^")

        return re.search(word, record)

    def specials_check():
        print("special situations check", file=string_out)

        # The following is based on Roger Frank's version of
        # PPTXT that is written in Go and available on the
        # online PPWB site. It uses tests extracted from
        # gutcheck that aren't supposed to be included in
        # earlier checks here.

        # METHOD
        #
        # Use a dictionary to collect reports on lines that contain
        # the 'specials' we are testing for. The keys are the report
        # headings (e.g. "full stop followed by letter") and the
        # value for the key is a list containing one or more records
        # that detail each line containing that 'special'. The records
        # are in 'output record' format; i.e. line number and text of
        # line and will be written directly to the log when all lines
        # in the book examined.

        specials_report = {}

        ## Allow Illustrations, Greek, Music or number in '[]'
        re0000 = re.compile(r"\[[^IGMS\d]")
        ## Punctuation after case-insensitive 'the'.
        re0001 = re.compile(r"(?i)\bthe\p{P}")
        ## Double punctuation.
        re0002 = re.compile(r"(,\.)|(\.,)|(,,)|([^\.]\.\.[^\.])")
        ## For mixed case checks.
        re0003a1 = re.compile(r"..*?[\p{ll}].*?")
        re0003b1 = re.compile(r"..*?[\p{lu}].*?")
        re0003a2 = re.compile(r"...*?[\p{ll}].*?")
        re0003b2 = re.compile(r"...*?[\p{lu}].*?")
        ### For mixed case checks - very rare to end word.
        re0003c = re.compile("cb|gb|pb|sb|tb|wh|fr|br|qu|tw|gl|fl|sw|gr|sl|cl|iy")
        ### For mixed case checks - very rare to start word.
        re0003d = re.compile("hr|hl|cb|sb|tb|wb|tl|tn|rn|lt|tj")
        ### Single character line
        re0006 = re.compile("^.$")
        ### Broken hyphenation
        re0007 = re.compile(r"(\p{L}\- +?\p{L})|(\p{L} +?\-\p{L})")
        ### Comma spacing regexes
        re0008a = re.compile(r"\p{L},\p{L}")
        re0008b = re.compile(r"\p{L},\p{N}")
        re0008c = re.compile(r"\s,")
        re0008d = re.compile(r"^,")
        ### Oct. 8,2023 date fotmat
        re0010 = re.compile(r",[12]\p{Nd}{3}")
        ### I in place of intended !
        re0011 = re.compile(r"I”")
        ### Disjointed contraction. E.g "I 've"
        re0012 = re.compile(r"[A-Za-z]’ +?(m|ve|ll|t)\b")
        ### Title/honorific abbreviations
        re0013 = re.compile(r"Mr,|Mrs,|Dr,|Drs,|Messrs,|Ms,")
        ### Spaced punctuation
        re0014 = re.compile(r"\s[\?!:;]")

        ### HTML tag (Done in a standalone check so removed from here)
        ### Now the first standalone check done and used to warn user
        ### if file looks other than a text file; e.g. HTML or from
        ### fpgen.
        # re0016 = re.compile(r'(<(?=[!\/a-z]).*?(?<=[\"a-z0-9\/]|-)>)')
        ### Ellipses (Done in a standalone check so removed from here)
        # re0017 = re.compile(r"([^\.]\.\.\. )|(\.\.\.\.[^\s])|([^\.]\.\.[^\.])|(\.\.\.\.\.+")

        ### Quote direction (Done in a standalone check so could remove from here?))
        re0018 = re.compile(r"(((?<!M)[‘])|[\p{P}]+[‘“])|(\p{L}+[“])|(“ )|( ”)|(‘s\s)")
        ### Standalone 0
        re0019 = re.compile(r"\b0\b")
        ### Standalone 1 - general test
        re0020a = re.compile(r"(^|\P{Nd})1($|\P{Nd})")
        ### Standalone 1 - exceptions
        re0020b = re.compile(
            r"[\$£]1\b"
        )  # standalone 1 allowed after dollar/pound sign
        re0020c = re.compile(r"1,")  # standalone 1 allowed before comma
        re0020d = re.compile(
            r"1(-|‑|‒|–|—|―)\p{Nd}"
        )  # standalone 1 allowed before dash+num
        re0020e = re.compile(
            r"\p{Nd}(-|‑|‒|–|—|―)1"
        )  # standalone 1 allowed after num+dash
        re0020f = re.compile(
            r"(^|\P{Nd})1\."
        )  # standalone 1 allowed as "1." (a numbered list)
        re0020g = re.compile(r"1st")  # standalone 1 allowed as "1st"
        ## Words mixing alphas and digits - general test.
        re0021 = re.compile(r"(\p{L}\p{Nd})|(\p{Nd}\p{L})")
        ## Words mixing alphas and digits - exceptions to that test.
        re0021a = re.compile(r"(^|\P{L})\p{Nd}*[02-9]?1st(\P{L}|$)")
        re0021b = re.compile(r"(^|\P{L})\p{Nd}*[02-9]?2nd(\P{L}|$)")
        re0021c = re.compile(r"(^|\P{L})\p{Nd}*[02-9]?3rd(\P{L}|$)")
        re0021d = re.compile(r"(^|\P{L})\p{Nd}*[4567890]th(\P{L}|$)")
        re0021e = re.compile(r"(^|\P{L})\p{Nd}*1\p{Nd}th(\P{L}|$)")
        re0021f = re.compile(r"(^|\P{L})\p{Nd}*[23]d(\P{L}|$)")
        ## Abbreviation &c without period
        re0023 = re.compile(r"&c([^\.]|$)")
        ## Line starts with (selected) punctuation
        re0024 = re.compile(r"^[!;:,.?]")
        ## Line starts with hyphen followed by non-hyphen
        re0025 = re.compile(r"^-[^-]")

        ## Periods should not occur after these words
        no_period_pattern = (
            r"\P{L}(every\.|i’m\.|during\.|that’s\.|their\.|your\.|our\.|my\.|or\."
            r"|and\.|but\.|as\.|if\.|the\.|its\.|it’s\.|until\.|than\.|whether\.|i’ll\."
            r"|whose\.|who\.|because\.|when\.|let\.|till\.|very\.|an\.|among\.|those\."
            r"|into\.|whom\.|having\.|thence\.)"
        )
        re_period = re.compile(no_period_pattern)

        ## Commas should not occur after these words
        no_comma_pattern = (
            r"\P{L}(the,|it’s,|their,|an,|a,|our,|that’s,|its,|whose,|every,"
            r"|i’ll,|your,|my,|mr,|mrs,|mss,|mssrs,|ft,|pm,|st,|dr,|rd,|pp,|cf,"
            r"|jr,|sr,|vs,|lb,|lbs,|ltd,|i’m,|during,|let,|toward,|among,)"
        )
        re_comma = re.compile(no_comma_pattern)

        ## Paragraph ends in a comma?
        cnt = 0
        for line in book:
            if cnt < len(book) - 1 and line.endswith(",") and book[cnt + 1] == "":
                heading = "\nparagraph ends in comma"
                if heading in specials_report:
                    specials_report[heading].append(make_a_report_record(cnt + 1, line))
                else:
                    specials_report[heading] = [make_a_report_record(cnt + 1, line)]
            cnt += 1

        #####
        # The following series of checks operate on each line of the book.
        ####

        line_index = 0
        for line in book:
            ## Mixed letters/digits in a word. Note the exceptions.
            if (
                re0021.search(line)
                and not re0021a.search(line)
                and not re0021b.search(line)
                and not re0021c.search(line)
                and not re0021d.search(line)
                and not re0021e.search(line)
                and not re0021f.search(line)
            ):
                heading = "\nmixed letters and digits in word"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if res := re0000.search(line):
                heading = "\nopening square bracket followed by other than I, G, M, S or number"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if res := re0001.search(line):
                # Ignore contexts such as "Will-o’-the-wisp"
                line_copy = line.replace("-the-", "-")
                # Try again after eliminating the above context from line
                if res := re0001.search(line_copy):
                    heading = "\npunctuation after 'the'"
                    if heading in specials_report:
                        specials_report[heading].append(
                            make_a_report_record(line_index + 1, line)
                        )
                    else:
                        specials_report[heading] = [
                            make_a_report_record(line_index + 1, line)
                        ]

            if res := re0002.search(line):
                # Ignore contexts such as "etc.,"
                line_copy = line.replace("etc.,", " ")
                line_copy = line_copy.replace("&c.,", " ")
                # Try again after eliminating the above context(s) from line
                if res := re0002.search(line):
                    heading = "\npunctuation error"
                    if heading in specials_report:
                        specials_report[heading].append(
                            make_a_report_record(line_index + 1, line)
                        )
                    else:
                        specials_report[heading] = [
                            make_a_report_record(line_index + 1, line)
                        ]

            ##
            # The following series of tests operate on words within the line.
            ##

            in_good_words_list = False  # Temporary until decision on loading 'good words' and/or 'proj dict'.

            # re0003* - check each word separately
            for word in line_word_list[line_index]:
                # Check for mixed case within word after the first character,
                # or after the second character if the first is "’" but not
                # if the word is in the good word list or it occurs more than
                # once in the book. NB Until inputting good words/proj dictionary
                # implemented assume not in good words list so word is always
                # reported.

                reportme = False
                if book_word_count[word] < 2 and not in_good_words_list:
                    # NB The first test above also means the word is never
                    #    repeated on a line as it appears only once in book.

                    if word.startswith("’"):
                        # Check lower + upper in word after the second character.
                        if re0003a2.match(word) and re0003b2.match(word):
                            reportme = True
                    else:
                        # Check lower + upper in word after the first character.
                        if re0003a1.match(word) and re0003b1.match(word):
                            reportme = True
                if reportme:
                    heading = "\nmixed case within word"
                    output_record = make_a_report_record(line_index + 1, line)

                    # Highlight the word within the output record just generated.

                    if res := regex_search(word, output_record):
                        output_record = decorate(
                            output_record, [(res.start(), len(word))], "redonyellow"
                        )
                        if heading in specials_report:
                            specials_report[heading].append(output_record)
                        else:
                            specials_report[heading] = [output_record]

                if len(word) > 2:
                    # Check word endings (last 2 characters)
                    last2 = word[len(word) - 2 :]
                    if res := re0003c.match(last2):
                        template = "\nquery word ending with {}"
                        heading = template.format(last2)
                        output_record = make_a_report_record(line_index + 1, line)
                        # Find the suspect word on the output record and highlight it.
                        if res := regex_search(
                            word, output_record
                        ):  # Belt-n-braces. Should always match.
                            output_record = decorate(
                                output_record, [(res.start(), len(word))], "redonyellow"
                            )
                            if heading in specials_report:
                                specials_report[heading].append(output_record)
                            else:
                                specials_report[heading] = [output_record]
                    # Check word start (first 2 characters)
                    first2 = word[0:2]
                    if res := re0003d.match(first2):
                        template = "\nquery word starting with {}"
                        heading = template.format(first2)
                        output_record = make_a_report_record(line_index + 1, line)
                        # Find the suspect word on the output record and highlight it.
                        if res := regex_search(
                            word, output_record
                        ):  # Belt-n-braces. Should always match.
                            output_record = decorate(
                                output_record, [(res.start(), len(word))], "redonyellow"
                            )
                            if heading in specials_report:
                                specials_report[heading].append(output_record)
                            else:
                                specials_report[heading] = [output_record]

            ##
            # We're back to testing whole line again.
            ##

            if res := re0006.search(line):
                heading = "\nsingle character line"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if res := re0007.search(line):
                heading = "\nbroken hyphenation"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if (
                re0008a.search(line)
                or re0008b.search(line)
                or re0008c.search(line)
                or re0008d.search(line)
            ):
                heading = "\ncomma spacing"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if res := re0010.search(line):
                heading = "\ndate format"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if res := re0011.search(line):
                heading = "\nI/! check"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if res := re0012.search(line):
                heading = "\ndisjointed contraction"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if res := re0013.search(line):
                heading = "\ntitle abbreviation + comma"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if res := re0014.search(line):
                heading = "\nspaced punctuation"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if res := re0018.search(line):
                heading = "\nquote error (context)"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if res := re0019.search(line):
                heading = "\nstandalone 0"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if (
                re0020a.search(line)
                and not re0020b.search(line)
                and not re0020c.search(line)
                and not re0020d.search(line)
                and not re0020e.search(line)
                and not re0020f.search(line)
                and not re0020g.search(line)
            ):
                heading = "\nstandalone 1"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if res := re0023.search(line):
                heading = "\nabbreviation &c without period"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if res := re0024.search(line):
                heading = "\nline start with suspect punctuation"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if res := re0025.search(line):
                heading = "\nline start with hyphen and then non-hyphen"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            ##
            # Non-regex based checks
            ##

            if "Blank Page" in line:
                heading = "\nBlank Page place holder found"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if "—-" in line or "-—" in line or "–-" in line or "-–" in line:
                heading = "\nmixed hyphen/dashd in line"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if "\u00A0" in line:
                heading = "\nnon-breaking space"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if "\u00AD" in line:
                heading = "\nsoft hyphen in line"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if "\u0009" in line:
                heading = "\ntab character in line"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if "&" in line and not "&#" in line:
                heading = "\nampersand character in line (excluding unicode numeric character references)"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            lc_line = line.lower()
            if re_comma.search(lc_line):
                heading = "\nunexpected comma after certain words"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            if re_period.search(lc_line):
                heading = "\nunexpected period after certain words"
                if heading in specials_report:
                    specials_report[heading].append(
                        make_a_report_record(line_index + 1, line)
                    )
                else:
                    specials_report[heading] = [
                        make_a_report_record(line_index + 1, line)
                    ]

            line_index += 1

        # We have at this point a dictionary of headings and accompanying line
        # text, etc., that are formatted as complete records ready to be written
        # to the output file. So just output the whole dictionary.

        for heading in sorted(specials_report):
            print(heading, file=string_out)
            for record in specials_report[heading]:
                print(record, file=string_out)

        # We may get here without finding any 'specials' entries.
        if len(specials_report) == 0:
            print("\n    no special situations reports.", file=string_out)

        # All done! Write the rule that terminates this section of the report.
        template = "\n{}"
        print(template.format("-" * 80), file=string_out)

    # PPTXT main part

    long_doctype_decl = False
    book = []
    paras = []
    line_word_list = []
    book_word_count = {}

    # Read book a line at a time into list 'book[]' as a text string
    # then gather and count the 'words' on each line. See the function
    # 'get_words_on_line()' for its definition of a 'word'.

    for line in string_in:
        line = line.rstrip("\n")
        line = line.rstrip("\r")

        book.append(line)

        # Build a list, 'line_word_list', whose entries are themselves
        # a list of words on each line. It is indexed from zero and
        # will have as many entries as there are lines in the book.

        # At the same time, keep a count of the number of times a word
        # occurs in the book.

        wol = get_words_on_line(line)
        line_word_list.append(wol)
        for word in wol:
            if word in book_word_count:
                book_word_count[word] += 1
            else:
                book_word_count[word] = 1

    # Rewind input stream and read book again a paragraph at a time.

    string_in.seek(0)

    # The lines are buffered and only appended to the 'paras' string
    # when either a blank line is encountered or end of input file.

    # Ignore leading blank lines in file
    ignore = True

    re_blnk = re.compile(r"^ +?$")

    for line in string_in:
        line = line.rstrip("\n")
        line = line.rstrip("\r")

        # The logic used in the tests implemented by this program
        # assumes that a 'blank line' has zero length. Make sure
        # this is so.

        if re_blnk.match(line):
            line = ""

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

    # End of book. If anything in the buffer add it to 'paras' string

    if len(buffer) > 0:
        paras.append(buffer)

    ###################################################
    # We're done reading the input. Start processing it.
    ###################################################

    # Prefix output with a divider line. Done here as each
    # check below only writes a divider when it's finished.

    print(" ", file=string_out)
    template = "{}"
    print(template.format("-" * 80), file=string_out)

    # The checks are run in the following order...

    html_check()
    uniocode_numeric_character_check()
    asterisk_check()
    adjacent_spaces()
    trailing_spaces()
    weird_characters()
    spacing_check()
    short_lines_check()
    long_lines_check()
    repeated_words_check()
    ellipses_check()
    dash_review()
    curly_quote_check()
    scanno_check()
    # This final one does multiple checks.
    specials_check()


#########################################
#
# MAIN PROGRAM
#
#########################################
if __name__ == "__main__":
    if platform.system() == "Windows":
        os.system("color")

    # Usage and command line arguments

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "INPUT", type=lambda x: is_valid_file(parser, x), help="input text file"
    )
    parser.add_argument(
        "-o",
        "--output",
        help="report on each check carried out",
        type=argparse.FileType("w", encoding="UTF-8"),
    )
    parser.add_argument(
        "-d",
        "--decorate",
        help="use colour to highlight in report",
        action="store_true",
    )
    parser.add_argument("-v", "--verbose", help="verbose output", action="store_true")
    args = parser.parse_args()

    # Positional argument - input text
    srcfile = args.INPUT

    # Default log output
    log = sys.stdout

    # Redirect log output if optional output file specified

    if args.output:
        logfile = args.output.name
        log = open(logfile, "w", encoding="utf-8")

    log.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

    # Decorate (aka 'highlighting') is an optional argument

    highlight = False
    if args.decorate:
        highlight = True

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

    input = open(srcfile, "r", encoding="utf-8")

    # Read whole book into a string buffer
    buffer = ""
    for line in input:
        buffer += line

    input.close()

    # Create an input text stream using the full buffer just
    # created.

    string_in = io.StringIO(buffer)

    # Create an output text stream with an empty buffer.

    string_out = io.StringIO()

    # Call pptxt to process the input text buffer and pass
    # back a filled output text buffer.

    pptxt(string_in, string_out, verbose=verbose, highlight=highlight)

    # Write the output buffer to the log file.

    string_out.seek(0)
    for line in string_out:
        line = line.rstrip("\n")
        line = line.rstrip("\r")
        print(line, file=log)

    log.close()
    string_in.close()
    string_out.close()
