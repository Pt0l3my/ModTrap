{
  ModTrap's second script for xEdit (ModTrap's design, section 6.3). Our own code; MIT licence.

  NOT USED YET: ModTrap does not start xEdit with this script until its read-only script (ModTrap.pas) has been
  proven on a real modlist and this one on ModTrap's own invented plugins (the probe).

  It changes the dependant plugins IN MEMORY ONLY, exactly as the job says, writes each finished plugin to a NEW
  file in ModTrap's own folder, and then takes the "changed" mark off every loaded plugin, so that xEdit saves
  nothing over any original when it closes.

  The job is modtrap-job.txt beside this script, key=value lines written by ModTrap:
    format=modtrap-job/1  mode=apply  out=<report file>  progress=<progress file>  outdir=<folder for new files>
    trap.count / trap.N       the trapped plugins
    dep.count  / dep.N        the dependant plugins to demaster
    do.N.count / do.N.M       what to take out of dependant N, in the order given:
        <form id>|R                  the record itself (it belongs to a trapped plugin)
        <form id>|E|<i/j/k>|<name>   the element reached from the record by taking element i, then j of that,
                                     then k of that; <name> is what that element must be called
  Nothing is taken out unless it is what the job says it is: a record must belong to a trapped plugin, an element
  must have the expected name and must itself need a trapped plugin. One refusal and that dependant is not written.

  The report, tab-separated:
    H  format, mode, xEdit's version
    A  an action: file, form id, R or E, "ok" or "refused", the reason
    C  after the actions and Clean Masters: file, its masters now (comma separated), records still needing a
       trapped plugin, records now
    W  a finished plugin written: file, the new file's path
    K  a dependant kept as it was (nothing written): file, the reason
    M  a dependant not loaded: file
    X  the end: "ok" or "failed", and a reason
}
unit ModTrapApply;

var
  slJob, slOut, slProg, slTrap, slNeed: TStringList;
  sOut, sProg, sOutDir: string;
  gMissed: integer;

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

function FindRecord(f: IInterface; wantedForm: string): IInterface;
var
  i: integer;
  e: IInterface;
begin
  Result := nil;
  for i := 0 to Pred(RecordCount(f)) do begin
    e := RecordByIndex(f, i);
    if SameText(IntToHex(GetLoadOrderFormID(e), 8), wantedForm) then begin
      Result := e;
      Exit;
    end;
  end;
end;

// The n-th part of s, counting from 0, where parts are separated by sep. '' when there is none.
function Part(s, sep: string; n: integer): string;
var
  p, k: integer;
  rest: string;
begin
  Result := '';
  rest := s;
  k := 0;
  while True do begin
    p := Pos(sep, rest);
    if k = n then begin
      if p > 0 then
        Result := Copy(rest, 1, p - 1)
      else
        Result := rest;
      Exit;
    end;
    if p = 0 then
      Exit;
    rest := Copy(rest, p + Length(sep), Length(rest));
    Inc(k);
  end;
end;

// Follows a route such as 3/1/2 down from a record. Nothing when a step is not there.
function Follow(rec: IInterface; route: string): IInterface;
var
  k, idx: integer;
  step: string;
  cur: IInterface;
begin
  Result := nil;
  cur := rec;
  k := 0;
  while True do begin
    step := Part(route, '/', k);
    if step = '' then begin
      if k > 0 then
        Result := cur;
      Exit;
    end;
    idx := StrToInt(step);
    if (idx < 0) or (idx >= ElementCount(cur)) then
      Exit;
    cur := ElementByIndex(cur, idx);
    if not Assigned(cur) then
      Exit;
    Inc(k);
  end;
end;

// One action on one dependant. Returns '' when done, else why it was refused.
function DoAction(f: IInterface; action: string): string;
var
  form, what, route, expected: string;
  rec, target: IInterface;
begin
  Result := '';
  form := Part(action, '|', 0);
  what := Part(action, '|', 1);
  rec := FindRecord(f, form);
  if not Assigned(rec) then begin
    Result := 'the record is not in this plugin';
    Exit;
  end;
  if what = 'R' then begin
    if not IsTrapped(GetFileName(GetFile(MasterOrSelf(rec)))) then begin
      Result := 'the record does not belong to a trapped plugin';
      Exit;
    end;
    Remove(rec);
    Exit;
  end;
  if what = 'E' then begin
    route := Part(action, '|', 2);
    expected := Part(action, '|', 3);
    target := Follow(rec, route);
    if not Assigned(target) then begin
      Result := 'the element is not where the dry run found it';
      Exit;
    end;
    if Clean(Name(target)) <> expected then begin
      Result := 'the element there is called ' + Clean(Name(target)) + ', not ' + expected;
      Exit;
    end;
    if not NeedsTrapped(target) then begin
      Result := 'the element there does not need a trapped plugin';
      Exit;
    end;
    Remove(target);
    Exit;
  end;
  Result := 'an action this script does not know';
end;

procedure ApplyFile(f: IInterface; depIndex: integer);
var
  i, n, stillNeed: integer;
  fn, action, why, masters, outPath, refused: string;
  stillHas: boolean;
  fs: TFileStream;
begin
  fn := GetFileName(f);
  n := StrToInt(slJob.Values['do.' + IntToStr(depIndex) + '.count']);
  Say('changing ' + fn + ' in memory: ' + IntToStr(n) + ' thing(s) to take out');
  refused := '';
  for i := 0 to Pred(n) do begin
    action := slJob.Values['do.' + IntToStr(depIndex) + '.' + IntToStr(i)];
    why := DoAction(f, action);
    if why = '' then
      slOut.Add('A' + #9 + fn + #9 + Part(action, '|', 0) + #9 + Part(action, '|', 1) + #9 + 'ok' + #9)
    else begin
      slOut.Add('A' + #9 + fn + #9 + Part(action, '|', 0) + #9 + Part(action, '|', 1) + #9 + 'refused' + #9 + why);
      if refused = '' then
        refused := why;
    end;
  end;
  if refused <> '' then begin
    slOut.Add('K' + #9 + fn + #9 + 'an action was refused: ' + refused);
    Say('kept as it was: ' + fn + ' (' + refused + ')');
    Exit;
  end;
  CleanMasters(f);
  masters := '';
  stillHas := False;
  for i := 0 to Pred(MasterCount(f)) do begin
    if i > 0 then
      masters := masters + ',';
    masters := masters + GetFileName(MasterByIndex(f, i));
    if IsTrapped(GetFileName(MasterByIndex(f, i))) then
      stillHas := True;
  end;
  stillNeed := 0;
  for i := 0 to Pred(RecordCount(f)) do
    if NeedsTrapped(RecordByIndex(f, i)) then
      Inc(stillNeed);
  slOut.Add('C' + #9 + fn + #9 + masters + #9 + IntToStr(stillNeed) + #9 + IntToStr(RecordCount(f)));
  if stillHas or (stillNeed > 0) then begin
    slOut.Add('K' + #9 + fn + #9 + 'it still needs a trapped plugin after the changes (' + IntToStr(stillNeed) + ' record(s))');
    Say('kept as it was: ' + fn + ' still needs a trapped plugin');
    Exit;
  end;
  outPath := sOutDir + fn;
  fs := TFileStream.Create(outPath, fmCreate);
  try
    FileWriteToStream(f, fs, 0);
  finally
    fs.Free;
  end;
  slOut.Add('W' + #9 + fn + #9 + outPath);
  Say('written: ' + fn);
end;

procedure RunJob;
var
  i, n: integer;
  f: IInterface;
  depName: string;
begin
  slOut.Add('H' + #9 + 'modtrap-apply/1' + #9 + slJob.Values['mode'] + #9 + IntToStr(wbVersionNumber));
  n := StrToInt(slJob.Values['trap.count']);
  for i := 0 to Pred(n) do
    slTrap.Add(slJob.Values['trap.' + IntToStr(i)]);
  Say('xEdit has loaded ' + IntToStr(FileCount) + ' files');
  n := StrToInt(slJob.Values['dep.count']);
  for i := 0 to Pred(n) do begin
    depName := slJob.Values['dep.' + IntToStr(i)];
    f := FindFile(depName);
    if Assigned(f) then begin
      ApplyFile(f, i);
      SaveReport;
    end else begin
      slOut.Add('M' + #9 + depName);
      Say('not loaded: ' + depName);
    end;
  end;
end;

// Whatever happened above, no original may be saved over: the "changed" mark comes off every loaded plugin.
procedure ForgetChanges;
var
  i: integer;
begin
  for i := 0 to Pred(FileCount) do
    ClearElementState(FileByIndex(i), esUnsaved);
  Say('the changes in memory are dropped: xEdit will save nothing');
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
  slJob.LoadFromFile(ScriptsPath + 'modtrap-job.txt');
  sOut := slJob.Values['out'];
  sProg := slJob.Values['progress'];
  sOutDir := slJob.Values['outdir'];
  if (slJob.Values['format'] <> 'modtrap-job/1') or (slJob.Values['mode'] <> 'apply') or (sOut = '') or (sProg = '') or (sOutDir = '') then begin
    AddMessage('ModTrap: the job file is not one this script understands; nothing was done.');
    Result := 1;
    Exit;
  end;
  Say('started');
  try
    try
      RunJob;
      slOut.Add('X' + #9 + 'ok' + #9);
    except
      on E: Exception do
        slOut.Add('X' + #9 + 'failed' + #9 + Clean(E.Message));
    end;
  finally
    ForgetChanges;
    SaveReport;
    Say('finished');
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
