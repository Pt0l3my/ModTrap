{
  ModTrap's script for xEdit: what the plugins a tool made hold of the mods that are to leave, compared by what
  the fields mean (ModTrap's design, section 34; MT23). Our own code; MIT licence. It changes nothing in any loaded
  plugin.

  The job is a text file beside this script, modtrap-job.txt, of key=value lines written by ModTrap:
    format=modtrap-job/1   mode=tools   out=<report file>   progress=<progress file>
    tool.count=N  tool.0=<plugin> ...     the plugins a tool made that are to be looked through
    gone.count=N  gone.0=<plugin> ...     the leaving plugins: those of the mods to take out, and the patches made
                                          for them
    made.count=N  made.0=<plugin> ...     every plugin a tool made: they have no say in which version of a record
                                          wins
  For each record a tool's plugin holds that a leaving plugin holds too, and on which a leaving plugin has the last
  word among the plugins no tool made, the tool's copy is compared, part by part (the record's direct elements),
  with the leaving plugin's version and with the version next in line: the last of the plugins that stay. A part
  in which those two say the same tells nothing. In any other part the tool's copy says what the leaving plugin
  says, or what the next in line says, or neither.
  The report is tab-separated lines; the first field says what the line is:
    H  format, mode, xEdit's version
    P  where xEdit looks for plugins (its data path), and how many files it has loaded
    F  a tool's plugin: file, records
    K  a record of it with a part that says what the leaving plugin says, or something of its own: file, form id,
       signature, the plugin the record belongs to, the leaving plugin, the plugin next in line ("" if none), and
       three lists of the parts' signatures (comma separated; ? where a part has none of its own): those that
       say what the leaving plugin says, those that say what the next in line says, those that say neither
    Y  a part of such a record, with the three values (cut short): file, form id, "mod" or "own", the part's
       name, the tool's value, the leaving plugin's, the next in line's; at most 80 for a plugin
    S  a tool's plugin is done: file, the records a leaving plugin holds too, of those the ones where a plugin
       that stays has the last word, then the records with a part that says what the leaving plugin says, with a
       part of its own and none of the leaving plugin's, with only parts of the next in line's, and with no
       part to tell apart
    M  a tool's plugin named in the job is not loaded: file
    N  a leaving plugin named in the job is not loaded: file
    U  a loaded plugin xEdit holds as changed although this script changed nothing: file
    X  the end: "ok" or "failed", and a reason
}
unit ModTrapTools;

var
  slJob, slOut, slProg, slGone, slMade: TStringList;
  sOut, sProg, gMod, gNext, gOwn: string;
  gMissed, gValues: integer;

function Clean(s: string): string;
begin
  Result := StringReplace(s, #9, ' ', [rfReplaceAll]);
  Result := StringReplace(Result, #13, ' ', [rfReplaceAll]);
  Result := StringReplace(Result, #10, ' ', [rfReplaceAll]);
end;

// A short wait. The script engine has no Sleep, so this watches the clock.
procedure Pause(ms: integer);
var
  until_, spins: double;
begin
  until_ := Now + ms / 86400000.0;
  spins := 0;
  while Now < until_ do
    spins := spins + 1;
end;

// The progress file is written whole each time; a missed write loses nothing (see ModTrapRecords.pas).
procedure Say(s: string);
begin
  slProg.Add(s);
  try
    slProg.SaveToFile(sProg);
  except
    gMissed := gMissed + 1;
  end;
  AddMessage('ModTrap: ' + s);
end;

// The report must be written: it is tried again for some seconds before the failure counts as the script's.
procedure SaveReport;
var
  tries: integer;
  saved: boolean;
begin
  saved := False;
  tries := 0;
  while (not saved) and (tries < 40) do begin
    try
      slOut.SaveToFile(sOut);
      saved := True;
    except
      tries := tries + 1;
      Pause(250);
    end;
  end;
  if not saved then
    slOut.SaveToFile(sOut);
end;

// An element with everything under it as text: names and values. Two elements with the same text hold the same.
// xEdit gives what a value means, not how it is written. Bytes the game does not use (xEdit calls them Unused)
// differ from plugin to plugin and mean nothing: they are left out.
function Shape(e: IInterface): string;
var
  i: integer;
  child: IInterface;
  sub, all: string;
begin
  if ElementCount(e) = 0 then begin
    Result := Clean(GetEditValue(e));
    Exit;
  end;
  all := '(';
  for i := 0 to Pred(ElementCount(e)) do begin
    child := ElementByIndex(e, i);
    if Clean(Name(child)) <> 'Unused' then begin
      sub := Shape(child);
      all := all + Clean(Name(child)) + '=' + sub + ';';
    end;
  end;
  Result := all + ')';
end;

// The part of that name in a record, as text; a part that is not there has a text of its own.
function ShapeOf(rec: IInterface; nm: string): string;
var
  pe: IInterface;
begin
  Result := '<not there>';
  if Assigned(rec) then begin
    pe := ElementByName(rec, nm);
    if Assigned(pe) then
      Result := Shape(pe);
  end;
end;

// The signatures of the fields an element stands for: its own if its name begins with one ("XCLR - Regions"),
// else those of the elements under it.
function SigsOf(el: IInterface): string;
var
  i: integer;
  nm, part, all: string;
begin
  nm := Name(el);
  if (Length(nm) > 6) and (Copy(nm, 5, 3) = ' - ') then begin
    Result := Copy(nm, 1, 4);
    Exit;
  end;
  all := '';
  for i := 0 to Pred(ElementCount(el)) do begin
    part := SigsOf(ElementByIndex(el, i));
    if part <> '' then begin
      if all <> '' then
        all := all + ',';
      all := all + part;
    end;
  end;
  Result := all;
end;

function CutShort(s: string): string;
begin
  if Length(s) > 160 then
    Result := Copy(s, 1, 160) + '...'
  else
    Result := s;
end;

function Joined(have, more: string): string;
begin
  if have = '' then
    Result := more
  else
    Result := have + ',' + more;
end;

// One part of a record: what the tool's copy says (mine), the leaving plugin's version (theirs) and the next in
// line's (after). Where the last two say the same there is nothing to tell apart.
procedure Tell(fn, recForm, nm, part, mine, theirs, after: string);
begin
  if theirs = after then
    Exit;
  if mine = theirs then begin
    gMod := Joined(gMod, part);
    if gValues < 80 then begin
      slOut.Add('Y' + #9 + fn + #9 + recForm + #9 + 'mod' + #9 + nm + #9 + CutShort(mine) + #9 + CutShort(theirs) + #9 + CutShort(after));
      gValues := gValues + 1;
    end;
  end else if mine = after then
    gNext := Joined(gNext, part)
  else begin
    gOwn := Joined(gOwn, part);
    if gValues < 80 then begin
      slOut.Add('Y' + #9 + fn + #9 + recForm + #9 + 'own' + #9 + nm + #9 + CutShort(mine) + #9 + CutShort(theirs) + #9 + CutShort(after));
      gValues := gValues + 1;
    end;
  end;
end;

procedure ReportTool(f: IInterface);
var
  i, j, k, cnt, order, modOrder, aftOrder, winOrder, held, lastElse, nMod, nOwn, nNext, nSame: integer;
  e, m, v, modv, aft, el: IInterface;
  fn, own, vfile, recForm, nm, part, aftName: string;
begin
  fn := GetFileName(f);
  cnt := RecordCount(f);
  slOut.Add('F' + #9 + fn + #9 + IntToStr(cnt));
  Say('reading ' + fn + ' (' + IntToStr(cnt) + ' records)');
  gValues := 0;
  held := 0;
  lastElse := 0;
  nMod := 0;
  nOwn := 0;
  nNext := 0;
  nSame := 0;
  for i := 0 to Pred(cnt) do begin
    e := RecordByIndex(f, i);
    m := MasterOrSelf(e);
    own := GetFileName(GetFile(m));
    if not SameText(own, fn) then begin
      modv := nil;
      aft := nil;
      modOrder := -1;
      aftOrder := -1;
      winOrder := -1;
      // Among the plugins no tool made: the last leaving plugin that holds the record, the last plugin that stays,
      // and which of all has the last word.
      for j := -1 to Pred(OverrideCount(m)) do begin
        if j < 0 then
          v := m
        else
          v := OverrideByIndex(m, j);
        vfile := GetFileName(GetFile(v));
        if slMade.IndexOf(vfile) < 0 then begin
          order := GetLoadOrder(GetFile(v));
          if order > winOrder then
            winOrder := order;
          if slGone.IndexOf(vfile) >= 0 then begin
            if order > modOrder then begin
              modOrder := order;
              modv := v;
            end;
          end else if order > aftOrder then begin
            aftOrder := order;
            aft := v;
          end;
        end;
      end;
      if Assigned(modv) then begin
        held := held + 1;
        if winOrder <> modOrder then
          lastElse := lastElse + 1
        else begin
          gMod := '';
          gNext := '';
          gOwn := '';
          recForm := IntToHex(GetLoadOrderFormID(e), 8);
          for k := 0 to Pred(ElementCount(e)) do begin
            el := ElementByIndex(e, k);
            nm := Name(el);
            if nm <> 'Record Header' then begin
              part := SigsOf(el);
              if part = '' then
                part := '?';
              Tell(fn, recForm, Clean(nm), part, Shape(el), ShapeOf(modv, nm), ShapeOf(aft, nm));
            end;
          end;
          // The parts the leaving plugin's version has and the tool's copy has not.
          for k := 0 to Pred(ElementCount(modv)) do begin
            el := ElementByIndex(modv, k);
            nm := Name(el);
            if nm <> 'Record Header' then
              if not Assigned(ElementByName(e, nm)) then begin
                part := SigsOf(el);
                if part = '' then
                  part := '?';
                Tell(fn, recForm, Clean(nm), part, '<not there>', Shape(el), ShapeOf(aft, nm));
              end;
          end;
          if gMod <> '' then
            nMod := nMod + 1
          else if gOwn <> '' then
            nOwn := nOwn + 1
          else if gNext <> '' then
            nNext := nNext + 1
          else
            nSame := nSame + 1;
          if (gMod <> '') or (gOwn <> '') then begin
            aftName := '';
            if Assigned(aft) then
              aftName := GetFileName(GetFile(aft));
            slOut.Add('K' + #9 + fn + #9 + recForm + #9 + Signature(e) + #9 + own + #9 + GetFileName(GetFile(modv)) + #9 +
              aftName + #9 + gMod + #9 + gNext + #9 + gOwn);
          end;
        end;
      end;
    end;
    if (i > 0) and (i mod 20000 = 0) then
      Say(fn + ': ' + IntToStr(i) + ' of ' + IntToStr(cnt) + ' records');
  end;
  slOut.Add('S' + #9 + fn + #9 + IntToStr(held) + #9 + IntToStr(lastElse) + #9 + IntToStr(nMod) + #9 + IntToStr(nOwn) + #9 +
    IntToStr(nNext) + #9 + IntToStr(nSame));
  SaveReport;
  Say('done ' + fn + ': ' + IntToStr(held) + ' record(s) a leaving plugin holds too; ' + IntToStr(nMod) + ' with its value, ' +
    IntToStr(nOwn) + ' with a value of the tool''s own');
end;

function FindFile(wanted: string): IInterface;
var
  i: integer;
begin
  Result := nil;
  for i := 0 to Pred(FileCount) do
    if SameText(GetFileName(FileByIndex(i)), wanted) then begin
      Result := FileByIndex(i);
      Exit;
    end;
end;

procedure RunJob;
var
  i, n: integer;
  f: IInterface;
  wantName: string;
begin
  slOut.Add('H' + #9 + 'modtrap-tools/1' + #9 + slJob.Values['mode'] + #9 + IntToStr(wbVersionNumber));
  Say('xEdit has loaded ' + IntToStr(FileCount) + ' files');
  slOut.Add('P' + #9 + DataPath + #9 + IntToStr(FileCount));
  n := StrToInt(slJob.Values['gone.count']);
  for i := 0 to Pred(n) do begin
    wantName := slJob.Values['gone.' + IntToStr(i)];
    slGone.Add(wantName);
    if not Assigned(FindFile(wantName)) then begin
      slOut.Add('N' + #9 + wantName);
      Say('not loaded: ' + wantName);
    end;
  end;
  n := StrToInt(slJob.Values['made.count']);
  for i := 0 to Pred(n) do
    slMade.Add(slJob.Values['made.' + IntToStr(i)]);
  n := StrToInt(slJob.Values['tool.count']);
  for i := 0 to Pred(n) do begin
    wantName := slJob.Values['tool.' + IntToStr(i)];
    f := FindFile(wantName);
    if Assigned(f) then
      ReportTool(f)
    else begin
      slOut.Add('M' + #9 + wantName);
      Say('not loaded: ' + wantName);
    end;
  end;
  // This script changed nothing. A plugin xEdit nonetheless holds as changed would be saved when xEdit closes:
  // say so, and take the mark away so that it is not.
  for i := 0 to Pred(FileCount) do begin
    f := FileByIndex(i);
    if GetElementState(f, esUnsaved) then begin
      slOut.Add('U' + #9 + GetFileName(f));
      Say('xEdit holds ' + GetFileName(f) + ' as changed; the mark is cleared so that it is not saved');
      ClearElementState(f, esUnsaved);
    end;
  end;
end;

function Initialize: integer;
begin
  Result := 0;
  gMissed := 0;
  slJob := TStringList.Create;
  slOut := TStringList.Create;
  slProg := TStringList.Create;
  slGone := TStringList.Create;
  slMade := TStringList.Create;
  slJob.LoadFromFile(ScriptsPath + 'modtrap-job.txt');
  sOut := slJob.Values['out'];
  sProg := slJob.Values['progress'];
  if (slJob.Values['format'] <> 'modtrap-job/1') or (slJob.Values['mode'] <> 'tools') or (sOut = '') or (sProg = '') then begin
    AddMessage('ModTrap: the job file is not one this script understands; nothing was done.');
    Result := 1;
    Exit;
  end;
  Say('started');
  try
    RunJob;
    slOut.Add('X' + #9 + 'ok' + #9);
    SaveReport;
    Say('finished');
  except
    on E: Exception do begin
      slOut.Add('X' + #9 + 'failed' + #9 + Clean(E.Message));
      SaveReport;
      Say('failed: ' + Clean(E.Message));
      raise;
    end;
  end;
end;

function Finalize: integer;
begin
  Result := 0;
  slJob.Free;
  slOut.Free;
  slProg.Free;
  slGone.Free;
  slMade.Free;
end;

end.
