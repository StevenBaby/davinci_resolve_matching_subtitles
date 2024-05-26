import os
import sys
import re
import traceback
import datetime
import tempfile

__version__ = "0.2.0"


def main():
    workon = os.path.expandvars("%WORKON_HOME%")
    if workon:
        active_this = r'%WORKON_HOME%\davinci\Scripts\activate_this.py'
        active_this = os.path.expandvars(active_this)
        if os.path.exists(active_this):
            exec(compile(open(active_this, "rb").read(), active_this, 'exec'), dict(__file__=active_this))
        # print(active_this)

    fu = resolve.Fusion()
    ui = fu.UIManager

    disp = bmd.UIDispatcher(ui)

    winID = "com.blackmagicdesign.resolve.SubtitleMatching"   # should be unique for single instancing
    textID = "TextEdit"
    matchID = "Matching"
    debugID = 'DebugID'
    methodID = "MethodID"

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

    ui_list = [
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
        ui.VGap(5),
        ui.Label({'Text': "Select Generate Method:", 'Weight': 0, 'Font': ui.Font({'PixelSize': 14})}),
        ui.ComboBox({"ID": methodID, 'MaximumSize': [1000, 35], }),
        ui.VGap(5),
        ui.Label({'Text': "Text + Template:", 'Weight': 0, 'Font': ui.Font({'PixelSize': 14})}),
        ui.ComboBox({"ID": "Template", 'MaximumSize': [1000, 35], }),
        ui.VGap(5),
        ui.Label({'ID': 'Message', 'Text': "", 'Weight': 0, 'Font': ui.Font({'PixelSize': 22, 'Bold': True})}),
        ui.VGap(5),
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
            if itemType == "Generator":
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

    def match_line(gens, line, index=0):
        from thefuzz import fuzz
        from pypinyin import pinyin
        import pypinyin

        line_pinyin = ''.join([var[0] for var in pinyin(line, style=pypinyin.NORMAL)])

        max_score = 0
        max_line = ''
        end = 0

        cur = ''
        # print(gens)
        for e in range(index, len(gens)):
            cur += gens[e][2]
            if len(cur) + 1 < len(line):
                continue

            cur_pinyin = ''.join([var[0] for var in pinyin(cur, style=pypinyin.NORMAL)])
            # print(cur_pinyin, line)

            score = fuzz.ratio(cur_pinyin, line_pinyin)
            if score > max_score:
                max_score = score
                max_line = cur
                end = e

        print(index, end)
        print(gens[index], gens[end])
        return end + 1, gens[index][0], gens[end][1], max_line

    def match_subtitle():
        from thefuzz import fuzz

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
        subs = []
        total = len(lines)
        for idx, line in enumerate(lines):
            show_message(f"Subtitle matching {(idx + 1) * 100 / total:0.2f} % .")
            if begin < len(gens):
                begin, start, end, max_line = match_line(gens, line, begin)
                subs.append((start, end, line))

        if items[methodID].CurrentIndex == 0:
            generate_srt_file(subs)
        else:
            generate_text(subs)

    def OnMatch(ev):
        items = win.GetItems()
        items['Message'].Text = "Subtitle matching..."
        try:
            from thefuzz import fuzz
            import srt
            import pypinyin
        except ImportError:
            print("Python environment error...")
            show_message(
                'Please install python package (thefuzz, srt, pypinyin)'
            )
            return
        except Exception as e:
            traceback.print_exc()
            show_message(e)

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
