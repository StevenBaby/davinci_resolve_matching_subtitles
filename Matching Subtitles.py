import os
import sys
import re
import traceback
import datetime
import tempfile

__version__ = "0.3.1"


def main():
    fu = resolve.Fusion()
    ui = fu.UIManager

    disp = bmd.UIDispatcher(ui)

    platform = sys.platform
    winID = "com.blackmagicdesign.resolve.SubtitleMatching"   # should be unique for single instancing
    textID = "TextEdit"
    matchID = "Matching"
    debugID = 'DebugID'
    methodID = "MethodID"
    virtualenvID = "VIRTUALENV"

    win = ui.FindWindow(winID)
    if win:
        win.Show()
        win.Raise()
        exit()

    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject()
    mediapool = project.GetMediaPool()
    framerate = project.GetSetting('timelineFrameRate')
    timeline = project.GetCurrentTimeline()

    logoPath = fu.MapPath(r"AllData:../Support/Developer/Workflow Integrations/Examples/SamplePlugin/img/logo.png")
    header = '<html><body><h1 style="vertical-align:middle;">'
    header = header + '<img src="' + logoPath + '"/>&nbsp;&nbsp;&nbsp;'
    header = header + f'<b>Resolve Matching Subtitles'
    header = header + '</h1></body></html>'

    environ_placeholder = r"%WORKON_HOME%\davinci\Scripts\activate_this.py"
    if platform == "win32":
        pass
    elif platform in ("linux", "linux2"):
        environ_placeholder = "$WORKON_HOME/davinci/bin/activate_this.py"
    elif platform == "darwin":  # OSX
        environ_placeholder = "$WORKON_HOME/davinci/bin/activate_this.py"

    ui_list = [
        ui.VGap(10),
        ui.Label({'Text': header, 'Weight': 0.1}),
        ui.VGap(10),
        ui.Label({'Text': "Subtitles:", 'Weight': 0, 'Font': ui.Font({'PixelSize': 14})}),
        ui.TextEdit({
            'ID': textID,
            #  'TabStopWidth': 28,
            'LineWrapMode': "NoWrap",
            'AcceptRichText': False,
            # Use python lexer for syntax highlighting; other options include lua, html, json, xml, markdown, cpp, glsl, etc...
            'Lexer': "python",
        }),
        ui.VGroup({'Weight': 1, }, [
            ui.VGap(5),
            ui.Label({'Text': "Custom Python Virtual Environment:", 'Weight': 0, 'Font': ui.Font({'PixelSize': 14})}),
            ui.LineEdit({
                'ID': virtualenvID,
                'LineWrapMode': "NoWrap",
                'PlaceholderText': environ_placeholder,
                'AcceptRichText': False,
            }),
        ]),

        ui.VGroup({'Weight': 1, }, [
            ui.VGap(5),
            ui.Label({'Text': "Select Generate Method:", 'Weight': 0, 'Font': ui.Font({'PixelSize': 14})}),
            ui.ComboBox({"ID": methodID, 'MaximumSize': [1000, 35], }),
        ]),

        ui.VGroup({'Weight': 1, }, [
            ui.VGap(5),
            ui.Label({'Text': "Text + Template:", 'Weight': 0, 'Font': ui.Font({'PixelSize': 14})}),
            ui.ComboBox({"ID": "Template", 'MaximumSize': [1000, 35], }),
        ]),

        ui.Label({'ID': 'Message', 'Text': "", 'Weight': 0, 'Font': ui.Font({'PixelSize': 22, 'Bold': True})}),
        ui.Button({'ID': matchID, 'Text': "Match", 'MinimumSize': [120, 35], 'MaximumSize': [1000, 35], }),
    ]

    # define the window UI layout
    win = disp.AddWindow({
        'ID': winID,
        # 'Geometry': [100, 100, 600, 400],
        'WindowTitle': f"Resolve Matching Subtitles v{__version__}",
    },
        ui.VGroup({"ID": "root", }, ui_list),
    )

    items = win.GetItems()

    items[methodID].AddItem("Subtitle File")
    items[methodID].AddItem("Text+ Video Track")

    mediaPoolItemsList = []

    def recursiveSearch(folder):
        clips = folder.GetClipList()
        for item in clips:
            itemType = item.GetClipProperty()["Type"]

            if itemType in ('Fusion Title', "Generator"):
                itemName = item.GetName()
                clipName = item.GetClipProperty()['Clip Name']
                items['Template'].AddItem(clipName)
                if re.search('text|Text|title|Title|subtitle|Subtitle', itemName) or \
                        re.search('text|Text|title|Title|subtitle|Subtitle', clipName):
                    items['Template'].CurrentIndex = len(mediaPoolItemsList) - 1  # set default template to Text+
                mediaPoolItemsList.append(item)

        subfolders = folder.GetSubFolderList()
        for subfolder in subfolders:
            recursiveSearch(subfolder)
        return

    def searchMediaPool():
        folder = mediapool.GetRootFolder()
        items['Template'].Clear()
        items['Template'].SetEnabled(False)
        recursiveSearch(folder)

    searchMediaPool()

    if timeline:
        subitems = timeline.GetItemListInTrack('subtitle', 1)
        contents = []
        frame = 0
        if subitems:
            gens = []
            for sub in subitems:
                if sub.GetStart() > frame + framerate * 2:
                    contents.append(''.join([
                        var[2] for var in gens
                    ]))
                    gens = []
                    frame = sub.GetStart()
                gens.append([sub.GetStart(), sub.GetEnd(), sub.GetName()])
            contents.append(''.join([var[2] for var in gens]))

        items[textID].Text = '\n'.join([var for var in contents if var])

    def show_message(msg):
        items['Message'].Text = str(msg)

    def activate_environ():
        if platform not in {"win32", "linux", "linux2", "darwin"}:
            show_message("Unknown Operating System...")
            return False

        activate_this = win.Find(virtualenvID).Text.strip()
        if not activate_this:
            activate_this = environ_placeholder
        activate_this = os.path.expandvars(activate_this)

        if not os.path.exists(activate_this):
            show_message("invalid activate_this.py" + activate_this)
            return False

        with open(activate_this, "rb") as file:
            exec(compile(file.read(), activate_this, 'exec'), dict(__file__=activate_this))

    def try_import_requirements():
        from thefuzz import fuzz
        import srt
        import pypinyin
        return True

    def try_activate_environ():
        try:
            try_import_requirements()
            return True
        except ImportError:
            activate_environ()
        except Exception as e:
            traceback.print_exc()
            show_message(e)
            return False

        try:
            try_import_requirements()
            return True
        except ImportError:
            print("Python environment error...")
            show_message(
                'Please install python package (thefuzz, srt, pypinyin)'
            )
            return False
        except Exception as e:
            traceback.print_exc()
            show_message(e)
            return False

    def generate_srt_file(subs):
        import srt
        data = []
        for idx, (start, end, line) in enumerate(subs):
            sub = srt.Subtitle(
                index=idx,
                start=datetime.timedelta(seconds=start / framerate),
                end=datetime.timedelta(seconds=end / framerate),
                content=line
            )
            data.append(sub)

        result = srt.compose(data)
        with tempfile.TemporaryDirectory() as tempdir:
            filename = os.path.join(tempdir, f'Subtitle.srt')
            with open(filename, 'w', encoding='utf8') as file:
                file.write(result)

            medias = mediapool.ImportMedia(filename)
            if medias:
                show_message("Subtitle match finished...")

    def generate_text(subs):
        # folder = mediapool.GetCurrentFolder()
        if items['Template'].CurrentIndex < 0:
            show_message("Please select or create a template before match...")
            return

        mediaPoolItem = mediaPoolItemsList[items['Template'].CurrentIndex]

        timeline.AddTrack('video')
        trackindex = timeline.GetTrackCount('video')

        show_message("Create Text + clips to video track...")
        for start, end, line in subs:
            newClip = {
                "mediaPoolItem": mediaPoolItem,
                "startFrame": 0,
                "endFrame": end - start,
                "trackIndex": trackindex,
                "recordFrame": start,
            }
            mediapool.AppendToTimeline([newClip])

        show_message("Set content to Text + clips...")
        clipList = timeline.GetItemListInTrack('video', trackindex)
        if clipList:
            for idx, clip in enumerate(clipList):
                clip.SetClipColor('Orange')

                comp = clip.GetFusionCompByIndex(1)
                if comp:
                    toollist = list(comp.GetToolList().values())
                    for tool in toollist:
                        if tool.GetAttrs()["TOOLS_Name"] == 'Template':
                            comp.SetActiveTool(tool)
                            tool.SetInput('StyledText', subs[idx][2])
                clip.SetClipColor('Teal')

        show_message("Text video track created...")

    def to_pinyin(text):
        from pypinyin import pinyin
        import pypinyin
        return ''.join([var[0] for var in pinyin(text, style=pypinyin.NORMAL)])

    def match_subtitle():
        from thefuzz import fuzz
        if timeline is None:
            show_message("Create subtitle from audio before matching...")
            return

        items = win.GetItems()

        subitems = timeline.GetItemListInTrack('subtitle', 1)
        if not subitems:
            show_message("Create subtitle from audio before matching...")
            return

        # Each ASR segment: [start, end, text]. Precompute pinyin once so the
        # alignment loop never re-runs pinyin() on the same text.
        gens = []
        for sub in subitems:
            gens.append([sub.GetStart(), sub.GetEnd(), sub.GetName()])
        if not gens:
            items['Message'].Text = "This is not subtitles..."
            return

        gens_pinyin = [to_pinyin(g[2]) for g in gens]

        script = win.Find(textID).PlainText
        lines = [var for var in script.splitlines() if var]
        lines_pinyin = [to_pinyin(line) for line in lines]

        # Score how well a run of ASR segments [s..e] matches one correct line.
        # partial_ratio finds the line as a sub-run even when the ASR dropped or
        # added a few characters; ratio penalizes wrong characters; the length
        # factor penalizes spanning far more/fewer segments than the line needs,
        # so duplicates are not silently absorbed into a neighbouring line.
        def window_score(s, e, line_pinyin):
            cur = ''.join(gens_pinyin[s:e + 1])
            if not cur or not line_pinyin:
                return 0
            pr = fuzz.partial_ratio(cur, line_pinyin)
            r = fuzz.ratio(cur, line_pinyin)
            short = min(len(cur), len(line_pinyin))
            long = max(len(cur), len(line_pinyin))
            length_factor = short / long if long else 0
            return (0.7 * pr + 0.3 * r) * (0.4 + 0.6 * length_factor)

        # Global sequence alignment (Needleman-Wunsch style) over the ordered
        # correct lines and the ordered ASR segments. Each line maps to a
        # contiguous run of segments; extra/duplicate ASR segments may be skipped
        # (with a gap penalty) so they don't drag later subtitles forward.
        n = len(lines)
        m = len(gens)
        MAX_SPAN = 40   # cap segments a single line may span, keeps DP O(n*m*span)
        GAP = -15       # penalty for skipping one extra ASR segment

        NEG = float('-inf')
        # dp[i][j]: best score aligning the first i lines with the first j
        # segments. prev stores ('match', i-1, run_start) or ('skip', i, j-1).
        dp = [[NEG] * (m + 1) for _ in range(n + 1)]
        prev = [[None] * (m + 1) for _ in range(n + 1)]
        dp[0][0] = 0  # no leading skips: the first line starts at segment 0

        for i in range(1, n + 1):
            line_pinyin = lines_pinyin[i - 1]
            for j in range(1, m + 1):
                # Option 1: line i-1 matches a run [s .. j-1].
                best_val = NEG
                best_s = -1
                min_s = max(0, j - MAX_SPAN)
                for s in range(j - 1, min_s - 1, -1):
                    if dp[i - 1][s] == NEG:
                        continue
                    val = dp[i - 1][s] + window_score(s, j - 1, line_pinyin)
                    if val > best_val:
                        best_val = val
                        best_s = s
                # Option 2: skip segment j-1 (ASR extra/duplicate). A match wins ties.
                skip_val = dp[i][j - 1] + GAP if dp[i][j - 1] != NEG else NEG
                if best_val >= skip_val:
                    dp[i][j] = best_val
                    prev[i][j] = ('match', i - 1, best_s)
                else:
                    dp[i][j] = skip_val
                    prev[i][j] = ('skip', i, j - 1)

        # Backtrack the best path; trailing unaligned segments are ignored.
        best_j = max(range(0, m + 1), key=lambda j: dp[n][j])
        if dp[n][best_j] == NEG:
            show_message("Subtitle matching failed...")
            return

        alignment = []  # list of (seg_start_index, seg_end_index, line_index)
        i, j = n, best_j
        while i > 0 and j > 0:
            action, pi, pj = prev[i][j]
            if action == 'match':
                alignment.append((pj, j - 1, i - 1))
                i, j = pi, pj
            else:  # 'skip'
                i, j = pi, pj
        alignment.reverse()

        subs = []
        low_conf = 0
        for seg_start, seg_end, line_idx in alignment:
            line = lines[line_idx]
            score = window_score(seg_start, seg_end, lines_pinyin[line_idx])
            if score < 40:
                low_conf += 1
                print(f"Low confidence match ({score:0.1f}): {line!r}")
            start = gens[seg_start][0]
            end = gens[seg_end][1]
            subs.append((start, end, line))

        if items[methodID].CurrentIndex == 0:
            generate_srt_file(subs)
        else:
            generate_text(subs)

        if low_conf:
            show_message(f"Subtitle match finished ({low_conf} low-confidence lines, see console).")

    def OnMatch(ev):
        if not try_activate_environ():
            return
        show_message("activate environ success!!!")

        items = win.GetItems()
        items['Message'].Text = "Subtitle matching..."
        try:
            match_subtitle()
        except Exception as e:
            traceback.print_exc()
            show_message(e)
        finally:
            ...

    def OnClose(ev):
        disp.ExitLoop()

    def OnMethodChanged(ev):
        if items[methodID].CurrentIndex == 1:
            items['Template'].SetEnabled(True)
            if items['Template'].CurrentIndex < 0:
                show_message("Please select or create a template before match...")
        else:
            items['Template'].SetEnabled(False)

    def OnTemplateChanged(ev):
        if items['Template'].CurrentIndex < 0 and items[methodID].CurrentIndex == 1:
            items[matchID].SetEnabled(False)
        else:
            items[matchID].SetEnabled(True)
            show_message("")

    win.On[winID].Close = OnClose
    win.On[matchID].Clicked = OnMatch
    win.On[methodID].CurrentIndexChanged = OnMethodChanged
    win.On['Template'].CurrentIndexChanged = OnTemplateChanged

    win.Show()
    disp.RunLoop()
    win.Hide()


try:
    main()
except Exception:
    traceback.print_exc()
