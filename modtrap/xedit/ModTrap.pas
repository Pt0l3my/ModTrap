{
  ModTrap's script for xEdit (ModTrap's design, section 6.2). Our own code; MIT licence.

  Mode "report": for each dependant plugin named in the job, list every record and element that needs one of
  the trapped plugins. It changes nothing in any loaded plugin.

  The job is a text file beside this script, modtrap-job.txt, of key=value lines written by ModTrap:
    format=modtrap-job/1   mode=report   out=<report file>   progress=<progress file>
    trap.count=N  trap.0=<plugin> ...     dep.count=N  dep.0=<plugin> ...
  The report is tab-separated lines; the first field says what the line is:
    H  format, mode, xEdit's version
    F  a dependant: file, records, masters (comma separated)
    R  a record that needs a trapped plugin: file, signature, form id, the plugin the record belongs to,
       1 if that plugin is trapped (the dependant overrides a trapped plugin's own record) else 0, editor id
    E  an element of such a record that points at a trapped plugin: file, the record's form id, the element's
       path, the plugin and form id it points at, and the chain of elements from it up to its record (see ChainOf)
    C  for a record that belongs to another plugin, one line for each of its parts (the record's direct
       elements) that needs a trapped plugin, saying where that part comes from (see ReportCarried): file, the
       record's form id, the part's name, what kind of element it is, the plugin loaded before the dependant
       whose version of the part is the same ("" if none), the dependant's last master whose version of the
       part needs no trapped plugin ("" if none), how that version stands ("present", "absent", or "needs"
       and a plugin the dependant does not have as a master), how many entries of the part need a trapped
       plugin, and 1 if the part without those entries is what that master has, else 0
    D  a dependant is done: file, records, records needing a trapped plugin
    M  a dependant named in the job is not loaded: file
    U  a loaded plugin xEdit holds as changed although this script changed nothing: file
    P  where xEdit looks for plugins (its data path), and how many files it has loaded
    N  a trapped plugin named in the job is not loaded: file
    X  the end: "ok" or "failed", and a reason
}
unit ModTrap;

var
  slJob, slOut, slProg, slTrap, slNeed, slMasters, slFit: TStringList;
  sOut, sProg, gMissing: string;
  gMissed: integer;
  gTainted: integer;

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

// The progress file is written whole each time. Windows refuses the write while any other program has the file
// open, even for an instant (ModTrap reading it, a virus scanner looking at what was just written). A missed
// write loses nothing: the next line writes the whole list again, and the report says when the script has ended.
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


function IsTrapped(plugName: string): boolean;
begin
  Result := slTrap.IndexOf(plugName) >= 0;
end;

// Does this element, with everything under it, need a trapped plugin?
function NeedsTrapped(e: IInterface): boolean;
var
  i: integer;
begin
  Result := False;
  slNeed.Clear;
  ReportRequiredMasters(e, slNeed, False, True);
  for i := 0 to Pred(slNeed.Count) do
    if IsTrapped(slNeed[i]) then begin
      Result := True;
      Exit;
    end;
end;

// What lies between an element and its record, lowest first: for each step its name, what kind of element it is,
// what kind of value it holds, how many elements it holds and its place in the one above it. The parts of a step
// are separated by character 31, the steps by character 30. Whether a step is an entry of a list, and whether
// that list may be shortened, is ModTrap's to judge, not this script's.
function ChainOf(leaf: IInterface): string;
var
  cur, cont: IInterface;
  guard: integer;
begin
  Result := '';
  cur := leaf;
  guard := 0;
  while Assigned(cur) and (guard < 64) do begin
    if ElementType(cur) = etMainRecord then
      Exit;
    cont := GetContainer(cur);
    if Result <> '' then
      Result := Result + #30;
    Result := Result + Clean(Name(cur)) + #31 + ElementTypeAsText(cur) + #31 + DefTypeAsText(cur) + #31 +
      IntToStr(ElementCount(cur)) + #31 + IntToStr(IndexOf(cont, cur));
    cur := cont;
    Inc(guard);
  end;
end;

procedure ReportLeaf(plugName, recForm: string; leaf: IInterface);
var
  target: IInterface;
  linkFile, linkForm: string;
begin
  linkFile := '';
  linkForm := '';
  target := LinksTo(leaf);
  if Assigned(target) then
    if ElementType(target) = etMainRecord then begin
      linkFile := GetFileName(GetFile(MasterOrSelf(target)));
      linkForm := IntToHex(GetLoadOrderFormID(target), 8);
    end;
  slOut.Add('E' + #9 + plugName + #9 + recForm + #9 + Clean(Path(leaf)) + #9 + linkFile + #9 + linkForm + #9 + ChainOf(leaf));
end;

// An element with everything under it as text: names and values. Two elements with the same text hold the same.
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
    sub := Shape(child);
    all := all + Clean(Name(child)) + '=' + sub + ';';
  end;
  Result := all + ')';
end;

// The same text, leaving out the entries that need a trapped plugin; gTainted counts them.
function ShapeWithout(e: IInterface): string;
var
  i: integer;
  child: IInterface;
  sub, all: string;
begin
  gTainted := 0;
  all := '(';
  for i := 0 to Pred(ElementCount(e)) do begin
    child := ElementByIndex(e, i);
    if NeedsTrapped(child) then
      gTainted := gTainted + 1
    else begin
      sub := Shape(child);
      all := all + Clean(Name(child)) + '=' + sub + ';';
    end;
  end;
  Result := all + ')';
end;

// Does everything this element points at lie in the dependant or in its masters? If not, gMissing names one.
function Fits(e: IInterface; depName: string): boolean;
var
  i: integer;
begin
  Result := True;
  gMissing := '';
  slFit.Clear;
  ReportRequiredMasters(e, slFit, False, True);
  for i := 0 to Pred(slFit.Count) do
    if (slMasters.IndexOf(slFit[i]) < 0) and not SameText(slFit[i], depName) then begin
      Result := False;
      gMissing := slFit[i];
      Exit;
    end;
end;

// Where a part of a record comes from. The dependant overrides a record of another plugin, and this part of it
// (one of the record's direct elements) needs a trapped plugin. Among the versions of the record in the plugins
// loaded before the dependant, this finds the last whose version of the part is the same as the dependant's (the
// dependant then only carries that version on), and the last, in a master of the dependant that is not trapped,
// whose version needs no trapped plugin (what the part is without the trapped plugins). It only reads.
procedure ReportCarried(fn, recForm: string; rec, top: IInterface);
var
  m, v, vt: IInterface;
  i, myOrder, order, sameOrder, prevOrder, tainted: integer;
  mine, rest, vfile, sameFile, prevFile, prevState, prevShape, restSame: string;
begin
  m := MasterOrSelf(rec);
  myOrder := GetLoadOrder(GetFile(rec));
  mine := Shape(top);
  tainted := 0;
  rest := '';
  if (ElementTypeAsText(top) = 'etSubRecordArray') or (ElementTypeAsText(top) = 'etArray') then begin
    rest := ShapeWithout(top);
    tainted := gTainted;
  end;
  sameFile := '';
  prevFile := '';
  prevState := '';
  prevShape := '';
  sameOrder := -1;
  prevOrder := -1;
  for i := -1 to Pred(OverrideCount(m)) do begin
    if i < 0 then
      v := m
    else
      v := OverrideByIndex(m, i);
    order := GetLoadOrder(GetFile(v));
    if order < myOrder then begin
      vfile := GetFileName(GetFile(v));
      vt := ElementByName(v, Name(top));
      if Assigned(vt) then
        if (order > sameOrder) and (Shape(vt) = mine) then begin
          sameOrder := order;
          sameFile := vfile;
        end;
      if (order > prevOrder) and (not IsTrapped(vfile)) and (slMasters.IndexOf(vfile) >= 0) then begin
        if not Assigned(vt) then begin
          prevOrder := order;
          prevFile := vfile;
          prevState := 'absent';
          prevShape := '';
        end else if not NeedsTrapped(vt) then begin
          prevOrder := order;
          prevFile := vfile;
          prevShape := Shape(vt);
          if Fits(vt, fn) then
            prevState := 'present'
          else
            prevState := 'needs ' + gMissing;
        end;
      end;
    end;
  end;
  restSame := '0';
  if (tainted > 0) and (prevFile <> '') then
    if ((prevState = 'absent') and (rest = '()')) or ((prevState <> 'absent') and (rest = prevShape)) then
      restSame := '1';
  slOut.Add('C' + #9 + fn + #9 + recForm + #9 + Clean(Name(top)) + #9 + ElementTypeAsText(top) + #9 + sameFile + #9 +
    prevFile + #9 + prevState + #9 + IntToStr(tainted) + #9 + restSame);
end;

procedure ReportParts(fn, recForm: string; rec: IInterface);
var
  i: integer;
  top: IInterface;
begin
  for i := 0 to Pred(ElementCount(rec)) do begin
    top := ElementByIndex(rec, i);
    if CanContainFormIDs(top) then
      if NeedsTrapped(top) then
        ReportCarried(fn, recForm, rec, top);
  end;
end;

// Every lowest element under el that needs a trapped plugin.
procedure Walk(plugName, recForm: string; el: IInterface);
var
  i: integer;
  child: IInterface;
begin
  for i := 0 to Pred(ElementCount(el)) do begin
    child := ElementByIndex(el, i);
    if CanContainFormIDs(child) then
      if NeedsTrapped(child) then begin
        if ElementCount(child) > 0 then
          Walk(plugName, recForm, child)
        else
          ReportLeaf(plugName, recForm, child);
      end;
  end;
end;

procedure ReportFile(f: IInterface);
var
  i, n, hits: integer;
  e: IInterface;
  fn, own, recForm, masters, trapped: string;
begin
  fn := GetFileName(f);
  n := RecordCount(f);
  masters := '';
  slMasters.Clear;
  for i := 0 to Pred(MasterCount(f)) do begin
    if i > 0 then
      masters := masters + ',';
    masters := masters + GetFileName(MasterByIndex(f, i));
    slMasters.Add(GetFileName(MasterByIndex(f, i)));
  end;
  slOut.Add('F' + #9 + fn + #9 + IntToStr(n) + #9 + masters);
  Say('reading ' + fn + ' (' + IntToStr(n) + ' records)');
  hits := 0;
  for i := 0 to Pred(n) do begin
    e := RecordByIndex(f, i);
    if NeedsTrapped(e) then begin
      Inc(hits);
      own := GetFileName(GetFile(MasterOrSelf(e)));
      recForm := IntToHex(GetLoadOrderFormID(e), 8);
      if IsTrapped(own) then
        trapped := '1'
      else
        trapped := '0';
      slOut.Add('R' + #9 + fn + #9 + Signature(e) + #9 + recForm + #9 + own + #9 + trapped + #9 + Clean(EditorID(e)));
      if trapped = '0' then begin
        Walk(fn, recForm, e);
        ReportParts(fn, recForm, e);
      end;
    end;
    if (i > 0) and (i mod 5000 = 0) then
      Say(fn + ': ' + IntToStr(i) + ' of ' + IntToStr(n) + ' records, ' + IntToStr(hits) + ' need a trapped plugin');
  end;
  slOut.Add('D' + #9 + fn + #9 + IntToStr(n) + #9 + IntToStr(hits));
  SaveReport;
  Say('done ' + fn + ': ' + IntToStr(hits) + ' of ' + IntToStr(n) + ' records need a trapped plugin');
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
  depName: string;
begin
  slOut.Add('H' + #9 + 'modtrap-report/3' + #9 + slJob.Values['mode'] + #9 + IntToStr(wbVersionNumber));
  n := StrToInt(slJob.Values['trap.count']);
  for i := 0 to Pred(n) do
    slTrap.Add(slJob.Values['trap.' + IntToStr(i)]);
  Say('xEdit has loaded ' + IntToStr(FileCount) + ' files; ' + IntToStr(slTrap.Count) + ' trapped plugin(s)');
  slOut.Add('P' + #9 + DataPath + #9 + IntToStr(FileCount));
  for i := 0 to Pred(slTrap.Count) do
    if not Assigned(FindFile(slTrap[i])) then begin
      slOut.Add('N' + #9 + slTrap[i]);
      Say('not loaded: ' + slTrap[i]);
    end;
  n := StrToInt(slJob.Values['dep.count']);
  for i := 0 to Pred(n) do begin
    depName := slJob.Values['dep.' + IntToStr(i)];
    f := FindFile(depName);
    if Assigned(f) then
      ReportFile(f)
    else begin
      slOut.Add('M' + #9 + depName);
      Say('not loaded: ' + depName);
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
  slTrap := TStringList.Create;
  slNeed := TStringList.Create;
  slMasters := TStringList.Create;
  slFit := TStringList.Create;
  slJob.LoadFromFile(ScriptsPath + 'modtrap-job.txt');
  sOut := slJob.Values['out'];
  sProg := slJob.Values['progress'];
  if (slJob.Values['format'] <> 'modtrap-job/1') or (slJob.Values['mode'] <> 'report') or (sOut = '') or (sProg = '') then begin
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
      raise;    // on to xEdit, whose own log then names the line; ModTrap shows that log's last lines
    end;
  end;
end;

function Finalize: integer;
begin
  Result := 0;
  slJob.Free;
  slOut.Free;
  slProg.Free;
  slTrap.Free;
  slNeed.Free;
  slMasters.Free;
  slFit.Free;
end;

end.
