{
  ModTrap's script for xEdit: which records of a plugin override records of others, and who else changes the
  same records (ModTrap's design, section 16.5). Our own code; MIT licence. It changes nothing in any loaded plugin.

  The job is a text file beside this script, modtrap-job.txt, of key=value lines written by ModTrap:
    format=modtrap-job/1   mode=records   out=<report file>   progress=<progress file>
    new.count=N  new.0=<plugin> ...
  The report is tab-separated lines; the first field says what the line is:
    H  format, mode, xEdit's version
    F  a plugin: file, records, masters (comma separated)
    O  a record of it that overrides another plugin's record: file, signature, form id, editor id, xEdit's
       conflict level for the record over all plugins, xEdit's level for this plugin's copy of it (both as
       numbers, -1 when xEdit would not say), and every plugin holding the record, first the one it belongs to,
       then the overriding ones in load order, separated by character 31
    D  a plugin is done: file, records, records of its own, overriding records
    M  a plugin named in the job is not loaded: file
    P  where xEdit looks for plugins (its data path), and how many files it has loaded
    U  a loaded plugin xEdit holds as changed although this script changed nothing: file
    X  the end: "ok" or "failed", and a reason
}
unit ModTrapRecords;

var
  slJob, slOut, slProg: TStringList;
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

function LevelAll(e: IInterface): string;
begin
  Result := '-1';
  try
    Result := IntToStr(ConflictAllForMainRecord(e));
  except
    Result := '-1';
  end;
end;

function LevelThis(e: IInterface): string;
begin
  Result := '-1';
  try
    Result := IntToStr(ConflictThisForMainRecord(e));
  except
    Result := '-1';
  end;
end;

procedure ReportFile(f: IInterface);
var
  idx, jdx, cnt, ownCount, ovrCount: integer;
  e, firstRec: IInterface;
  plugName, masters, linkChain: string;
begin
  plugName := GetFileName(f);
  cnt := RecordCount(f);
  masters := '';
  for idx := 0 to Pred(MasterCount(f)) do begin
    if idx > 0 then
      masters := masters + ',';
    masters := masters + GetFileName(MasterByIndex(f, idx));
  end;
  slOut.Add('F' + #9 + plugName + #9 + IntToStr(cnt) + #9 + masters);
  Say('reading ' + plugName + ' (' + IntToStr(cnt) + ' records)');
  ownCount := 0;
  ovrCount := 0;
  for idx := 0 to Pred(cnt) do begin
    e := RecordByIndex(f, idx);
    if IsMaster(e) then
      Inc(ownCount)
    else begin
      Inc(ovrCount);
      firstRec := MasterOrSelf(e);
      linkChain := GetFileName(GetFile(firstRec));
      for jdx := 0 to Pred(OverrideCount(firstRec)) do
        linkChain := linkChain + #31 + GetFileName(GetFile(OverrideByIndex(firstRec, jdx)));
      slOut.Add('O' + #9 + plugName + #9 + Signature(e) + #9 + IntToHex(GetLoadOrderFormID(e), 8) + #9
        + Clean(EditorID(e)) + #9 + LevelAll(e) + #9 + LevelThis(e) + #9 + linkChain);
    end;
    if (idx > 0) and (idx mod 5000 = 0) then
      Say(plugName + ': ' + IntToStr(idx) + ' of ' + IntToStr(cnt) + ' records');
  end;
  slOut.Add('D' + #9 + plugName + #9 + IntToStr(cnt) + #9 + IntToStr(ownCount) + #9 + IntToStr(ovrCount));
  SaveReport;
  Say('done ' + plugName + ': ' + IntToStr(ovrCount) + ' of ' + IntToStr(cnt) + ' records override another plugin''s');
end;

function FindFile(wanted: string): IInterface;
var
  idx: integer;
begin
  Result := nil;
  for idx := 0 to Pred(FileCount) do
    if SameText(GetFileName(FileByIndex(idx)), wanted) then begin
      Result := FileByIndex(idx);
      Exit;
    end;
end;

procedure RunJob;
var
  idx, cnt: integer;
  f: IInterface;
  wantName: string;
begin
  slOut.Add('H' + #9 + 'modtrap-records/1' + #9 + slJob.Values['mode'] + #9 + IntToStr(wbVersionNumber));
  Say('xEdit has loaded ' + IntToStr(FileCount) + ' files');
  slOut.Add('P' + #9 + DataPath + #9 + IntToStr(FileCount));
  cnt := StrToInt(slJob.Values['new.count']);
  for idx := 0 to Pred(cnt) do begin
    wantName := slJob.Values['new.' + IntToStr(idx)];
    f := FindFile(wantName);
    if Assigned(f) then
      ReportFile(f)
    else begin
      slOut.Add('M' + #9 + wantName);
      Say('not loaded: ' + wantName);
    end;
  end;
  // This script changed nothing. A plugin xEdit nonetheless holds as changed would be saved when xEdit closes:
  // say so, and take the mark away so that it is not.
  for idx := 0 to Pred(FileCount) do begin
    f := FileByIndex(idx);
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
  slJob.LoadFromFile(ScriptsPath + 'modtrap-job.txt');
  sOut := slJob.Values['out'];
  sProg := slJob.Values['progress'];
  if (slJob.Values['format'] <> 'modtrap-job/1') or (slJob.Values['mode'] <> 'records') or (sOut = '') or (sProg = '') then begin
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
end;

end.
