import os
import sys
import traceback
import datetime
import tempfile

__version__ = "0.0.2"


def main():
    workon = os.path.expandvars("%WORKON_HOME%")
    if workon:
        active_this = r'%WORKON_HOME%\davinci\Scripts\activate_this.py'
        active_this = os.path.expandvars(active_this)
        if os.path.exists(active_this):
            exec(compile(open(active_this, "rb").read(), active_this, 'exec'), dict(__file__=active_this))
        # print(active_this)

    # import DaVinciResolveScript as dvr

    # resolve = dvr.scriptapp("Resolve")

    fu = resolve.Fusion()
    ui = fu.UIManager
    # disp = dvr.UIDispatcher(ui)

    disp = bmd.UIDispatcher(ui)

    winID = "com.blackmagicdesign.resolve.SubtitleMatching"   # should be unique for single instancing
    textID = "TextEdit"
    matchID = "Matching"

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
    header = header + '<b>Resolve Matching Subtitles</b>'
    header = header + '</h1></body></html>'

    # define the window UI layout
    win = disp.AddWindow({
        'ID': winID,
        # 'Geometry': [100, 100, 600, 400],
        'WindowTitle': "Resolve Matching Subtitles",
    },
        ui.VGroup({"ID": "root", }, [
            ui.VGap(10),
            ui.Label({'Text': header, 'Weight': 0.1}),
            ui.VGap(10),
            ui.TextEdit({
                'ID': textID,
                #  'TabStopWidth': 28,
                'LineWrapMode': "NoWrap",
                'AcceptRichText': False,
                # Use python lexer for syntax highlighting; other options include lua, html, json, xml, markdown, cpp, glsl, etc...
                'Lexer': "python",
            }),
            ui.Label({'ID': 'Message', 'Text': "", 'Weight': 0, 'Font': ui.Font({'PixelSize': 22, 'Bold': True})}),
            ui.VGap(10),
            ui.Button({'ID': matchID, 'Text': "Match", 'MinimumSize': [120, 35], 'MaximumSize': [1000, 35], }),
            # ui.TextBox(),
        ]),
    )

    items = win.GetItems()

    subitems = timeline.GetItemListInTrack('subtitle', 1)
    contents = []
    frame = 0
    if subitems:
        gens = []
        for sub in subitems:
            if sub.GetStart() > frame + framerate * 5:
                contents.append(''.join([
                    var[2] for var in gens
                ]))
                gens = []
                frame = sub.GetStart()
            gens.append([sub.GetStart(), sub.GetEnd(), sub.GetName()])

    items[textID].Text = '\n'.join([var for var in contents if var])

    def match_line(gens, line, index=0):
        from thefuzz import fuzz

        max_score = 0
        max_line = ''
        end = 0

        cur = ''
        # print(gens)
        for e in range(index, len(gens)):
            cur += gens[e][2]
            if len(cur) + 1 < len(line):
                continue

            score = fuzz.ratio(cur, line)
            if score > max_score:
                max_score = score
                max_line = cur
                end = e

        return end + 1, gens[index][0], gens[end][1], max_line

    def match_subtitle():
        from thefuzz import fuzz
        import srt
        items = win.GetItems()

        subitems = timeline.GetItemListInTrack('subtitle', 1)
        if not subitems:
            items['Message'].Text = "This is not subtitle track..."
            return

        gens = []
        for sub in subitems:
            gens.append([sub.GetStart(), sub.GetEnd(), sub.GetName()])
        if not gens:
            items['Message'].Text = "This is not subtitles..."
            return

        script = win.Find(textID).PlainText
        lines = [var for var in script.splitlines() if var]
        # print(lines)

        begin = 0
        index = 0
        subs = []
        for line in lines:
            begin, start, end, max_line = match_line(gens, line, begin)

            sub = srt.Subtitle(
                index=index,
                start=datetime.timedelta(seconds=start / framerate),
                end=datetime.timedelta(seconds=end / framerate),
                content=line
            )
            index += 1
            subs.append(sub)
            # print(sub)

        result = srt.compose(subs)
        with tempfile.TemporaryDirectory() as tempdir:
            filename = os.path.join(tempdir, f'Subtitle_{datetime.datetime.now().strftime("%H%M%S")}.srt')
            with open(filename, 'w', encoding='utf8') as file:
                file.write(result)

            medias = mediapool.ImportMedia(filename)
            if medias:
                items['Message'].Text = "Subtitle match finished..."

    def OnMatch(ev):
        items = win.GetItems()
        items['Message'].Text = "Subtitle matching..."
        try:
            from thefuzz import fuzz
            import srt
        except ImportError:
            print("Python environment error...")

            items['Message'].Text = "Python environment error..."
            return
        except Exception as e:
            print("Unknown error...")
            items['Message'].Text = str(e)

        try:
            match_subtitle()
            # disp.ExitLoop()
        except Exception as e:
            # print(e)
            traceback.print_exc()
            items['Message'].Text = str(e)
        finally:
            ...

    def OnClose(ev):
        # saveSettings()
        disp.ExitLoop()

    win.On[winID].Close = OnClose
    win.On[matchID].Clicked = OnMatch

    win.Show()
    disp.RunLoop()
    win.Hide()


try:
    main()
except Exception:
    traceback.print_exc()
