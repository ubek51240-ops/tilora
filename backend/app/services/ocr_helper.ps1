# Windows Native Media OCR Helper for TILORA
# Uses Windows.Media.Ocr to recognize text from image files

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$mGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethodDefinition } | Select-Object -First 1

function AwaitTask($asyncOp, $targetType) {
    $task = $mGeneric.MakeGenericMethod($targetType).Invoke($null, @($asyncOp))
    $task.Wait()
    return $task.Result
}

[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if (-not $engine) {
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('en-US'))
}

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

foreach ($img in $args) {
    if (-not (Test-Path $img)) { continue }
    try {
        $file = AwaitTask ([Windows.Storage.StorageFile]::GetFileFromPathAsync((Resolve-Path $img).Path)) ([Windows.Storage.StorageFile])
        $stream = AwaitTask ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
        $decoder = AwaitTask ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = AwaitTask ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $res = AwaitTask ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        Write-Host "=== PAGE_START ==="
        $res.Lines | ForEach-Object { Write-Host $_.Text }
        Write-Host "=== PAGE_END ==="
        $stream.Dispose()
    } catch {
        Write-Host "=== PAGE_START ==="
        Write-Host "=== PAGE_END ==="
    }
}
