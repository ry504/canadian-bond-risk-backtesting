Attribute VB_Name = "RefreshDashboard"
Option Explicit
'------------------------------------------------------------------------------
' RefreshDashboard - reloads the five Data_ tables from the CSVs written by Python
' (excel/*.csv). All Dashboard cells and charts are formulas / chart ranges
' on those tables, so reloading them refreshes the whole dashboard.
'
' Works on macOS and Windows: pure VBA file I/O only (no Shell, no ActiveX,
' no Windows-only libraries). Save this workbook as .xlsm in the SAME folder as
' the CSVs (excel/).
'------------------------------------------------------------------------------

Public Sub RefreshDashboard()
    Dim names As Variant, tbls As Variant, sheets As Variant
    Dim i As Long, folder As String, paths() As Variant, n As Long

    names = Array("daily.csv", "y2022.csv", "summary.csv", "stress.csv", "breaches2022.csv")
    tbls = Array("tblDaily", "tblY2022", "tblSummary", "tblStress", "tblBreaches2022")
    sheets = Array("Data_Daily", "Data_2022", "Data_Summary", "Data_Stress", "Data_Breaches2022")

    folder = ThisWorkbook.path
    If Len(folder) = 0 Then
        MsgBox "Save the workbook first (in the output/excel folder).", vbExclamation
        Exit Sub
    End If
    If Right$(folder, 1) <> Application.PathSeparator Then folder = folder & Application.PathSeparator

    ReDim paths(0 To UBound(names))
    For i = 0 To UBound(names)
        paths(i) = folder & names(i)
        If Dir(paths(i)) = "" Then
            MsgBox "Missing file: " & paths(i) & vbCrLf & "Run  python src/run_all.py  first.", vbExclamation
            Exit Sub
        End If
    Next i

    #If Mac Then
        ' macOS sandbox: ask the user once for read access to the CSVs
        If Not GrantAccessToMultipleFiles(paths) Then
            MsgBox "Excel needs permission to read the CSV files. Run again and click Allow/Select.", vbExclamation
            Exit Sub
        End If
    #End If

    On Error GoTo Fail
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual
    For i = 0 To UBound(names)
        n = LoadCsvToTable(paths(i), ThisWorkbook.Worksheets(sheets(i)).ListObjects(tbls(i)))
    Next i
    Application.Calculation = xlCalculationAutomatic
    Application.Calculate
    ThisWorkbook.names("LastRefreshed").RefersToRange.Value = Format$(Now, "yyyy-mm-dd hh:nn")
    Application.ScreenUpdating = True
    MsgBox "Dashboard refreshed from " & folder, vbInformation
    Exit Sub
Fail:
    Application.Calculation = xlCalculationAutomatic
    Application.ScreenUpdating = True
    MsgBox "Refresh failed: " & Err.Description, vbCritical
End Sub

' Replaces the data of one Excel Table with the contents of a CSV (header row + data rows).
' Returns the number of data rows loaded.
Private Function LoadCsvToTable(ByVal path As String, ByVal lo As ListObject) As Long
    Dim f As Integer, txt As String, lines() As String, parts() As String
    Dim nRows As Long, nCols As Long, r As Long, c As Long, k As Long
    Dim arr() As Variant, rng As Range

    f = FreeFile
    Open path For Binary Access Read As #f
    txt = Space$(LOF(f))
    Get #f, , txt
    Close #f
    txt = Replace(Replace(txt, vbCrLf, vbLf), vbCr, vbLf)
    lines = Split(txt, vbLf)

    ' count non-empty lines (first = header)
    For k = 0 To UBound(lines)
        If Len(Trim$(lines(k))) > 0 Then nRows = nRows + 1
    Next k
    nRows = nRows - 1
    If nRows < 1 Then Err.Raise vbObjectError + 1, , "No data rows in " & path

    nCols = UBound(Split(lines(0), ",")) + 1
    If nCols <> lo.ListColumns.Count Then _
        Err.Raise vbObjectError + 2, , "Column count mismatch in " & path & " (" & nCols & " vs " & lo.ListColumns.Count & ")"

    ReDim arr(1 To nRows, 1 To nCols)
    r = 0
    For k = 1 To UBound(lines)
        If Len(Trim$(lines(k))) > 0 Then
            r = r + 1
            parts = Split(lines(k), ",")
            For c = 1 To nCols
                If c - 1 <= UBound(parts) Then arr(r, c) = ParseField(parts(c - 1)) Else arr(r, c) = Empty
            Next c
        End If
    Next k

    ' clear, resize the table to the new row count, write values
    If Not lo.DataBodyRange Is Nothing Then lo.DataBodyRange.ClearContents
    lo.Resize lo.Range.Cells(1, 1).Resize(nRows + 1, nCols)
    Set rng = lo.DataBodyRange
    rng.Value = arr
    For c = 1 To nCols
        If VarType(arr(1, c)) = vbDate Then rng.Columns(c).NumberFormat = "yyyy-mm-dd"
    Next c
    LoadCsvToTable = nRows
End Function

' Converts a CSV field: yyyy-mm-dd -> Date, plain number -> Double (locale-independent), "" -> Empty, else text.
Private Function ParseField(ByVal s As String) As Variant
    s = Trim$(s)
    If Len(s) = 0 Then
        ParseField = Empty
    ElseIf s Like "####-##-##" Then
        ParseField = DateSerial(CInt(Left$(s, 4)), CInt(Mid$(s, 6, 2)), CInt(Right$(s, 2)))
    ElseIf IsPlainNumber(s) Then
        ParseField = Val(s)   ' Val always uses "." as decimal separator
    Else
        ParseField = s
    End If
End Function

Private Function IsPlainNumber(ByVal s As String) As Boolean
    Dim i As Long, ch As String, hasDigit As Boolean
    For i = 1 To Len(s)
        ch = Mid$(s, i, 1)
        If ch Like "[0-9]" Then
            hasDigit = True
        ElseIf Not (ch Like "[.eE+-]") Then
            Exit Function
        End If
    Next i
    IsPlainNumber = hasDigit
End Function
