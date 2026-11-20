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
    E  an element of such a record that points at a trapped plugin: file, the record's form id, kind
       ("entry" of an array, or "field"), the entry's path, the array's path, the array's length, the
       element's own path, the plugin and form id it points at
    D  a dependant is done: file, records, records needing a trapped plugin
    M  a dependant named in the job is not loaded: file
    U  a loaded plugin xEdit holds as changed although this script changed nothing: file
    X  the end: "ok" or "failed", and a reason
}
unit ModTrap;

var
  slJob, slOut, slProg, slTrap, slNeed: TStringList;
  sOut, sProg: string;

function Clean(s: string): string;
begin
  Result := StringReplace(s, #9, ' ', [rfReplaceAll]);
  Result := StringReplace(Result, #13, ' ', [rfReplaceAll]);
  Result := StringReplace(Result, #10, ' ', [rfReplaceAll]);
end;

procedure Say(s: string);
begin
  slProg.Add(s);
  slProg.SaveToFile(sProg);
  AddMessage('ModTrap: ' + s);
end;

procedure SaveReport;
begin
  slOut.SaveToFile(sOut);
end;

function IsTrapped(fileName: string): boolean;
begin
  Result := slTrap.IndexOf(fileName) >= 0;
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

// The element that would have to go if this one did: the element itself, or the nearest thing above it,
// that is an entry of an array. Nothing when there is no array between it and its record.
function EntryOf(leaf: IInterface): IInterface;
var
  cur, cont: IInterface;
begin
  Result := nil;
  cur := leaf;
  while Assigned(cur) do begin
    if ElementType(cur) = etMainRecord then
      Exit;
    cont := GetContainer(cur);
    if not Assigned(cont) then
      Exit;
    if (ElementType(cont) = etArray) or (ElementType(cont) = etSubRecordArray) then begin
      Result := cur;
      Exit;
    end;
    cur := cont;
  end;
end;

procedure ReportLeaf(fileName, formId: string; leaf: IInterface);
var
  entry, arr, target: IInterface;
  kind, entryPath, arrPath, arrLen, tFile, tForm: string;
begin
  entry := EntryOf(leaf);
  if Assigned(entry) then begin
    arr := GetContainer(entry);
    kind := 'entry';
    entryPath := Clean(Path(entry));
    arrPath := Clean(Path(arr));
    arrLen := IntToStr(ElementCount(arr));
  end else begin
    kind := 'field';
    entryPath := '';
    arrPath := '';
    arrLen := '0';
  end;
  tFile := '';
  tForm := '';
  target := LinksTo(leaf);
  if Assigned(target) then
    if ElementType(target) = etMainRecord then begin
      tFile := GetFileName(GetFile(MasterOrSelf(target)));
      tForm := IntToHex(GetLoadOrderFormID(target), 8);
    end;
  slOut.Add('E' + #9 + fileName + #9 + formId + #9 + kind + #9 + entryPath + #9 + arrPath + #9 + arrLen + #9 +
    Clean(Path(leaf)) + #9 + tFile + #9 + tForm);
end;

// Every lowest element under el that needs a trapped plugin.
procedure Walk(fileName, formId: string; el: IInterface);
var
  i: integer;
  child: IInterface;
begin
  for i := 0 to Pred(ElementCount(el)) do begin
    child := ElementByIndex(el, i);
    if CanContainFormIDs(child) then
      if NeedsTrapped(child) then begin
        if ElementCount(child) > 0 then
          Walk(fileName, formId, child)
        else
          ReportLeaf(fileName, formId, child);
      end;
  end;
end;

procedure ReportFile(f: IInterface);
var
  i, n, hits: integer;
  e: IInterface;
  fn, own, formId, masters, trapped: string;
begin
  fn := GetFileName(f);
  n := RecordCount(f);
  masters := '';
  for i := 0 to Pred(MasterCount(f)) do begin
    if i > 0 then
      masters := masters + ',';
    masters := masters + GetFileName(MasterByIndex(f, i));
  end;
  slOut.Add('F' + #9 + fn + #9 + IntToStr(n) + #9 + masters);
  Say('reading ' + fn + ' (' + IntToStr(n) + ' records)');
  hits := 0;
  for i := 0 to Pred(n) do begin
    e := RecordByIndex(f, i);
    if NeedsTrapped(e) then begin
      Inc(hits);
      own := GetFileName(GetFile(MasterOrSelf(e)));
      formId := IntToHex(GetLoadOrderFormID(e), 8);
      if IsTrapped(own) then
        trapped := '1'
      else
        trapped := '0';
      slOut.Add('R' + #9 + fn + #9 + Signature(e) + #9 + formId + #9 + own + #9 + trapped + #9 + Clean(EditorID(e)));
      if trapped = '0' then
        Walk(fn, formId, e);
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
  slOut.Add('H' + #9 + 'modtrap-report/1' + #9 + slJob.Values['mode'] + #9 + IntToStr(wbVersionNumber));
  n := StrToInt(slJob.Values['trap.count']);
  for i := 0 to Pred(n) do
    slTrap.Add(slJob.Values['trap.' + IntToStr(i)]);
  Say('xEdit has loaded ' + IntToStr(FileCount) + ' files; ' + IntToStr(slTrap.Count) + ' trapped plugin(s)');
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
  slJob := TStringList.Create;
  slOut := TStringList.Create;
  slProg := TStringList.Create;
  slTrap := TStringList.Create;
  slNeed := TStringList.Create;
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
end;

end.
