$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$r = Invoke-WebRequest -Uri "https://www.retio.or.jp/exam/past_ques_ans/other/" -UseBasicParsing
$links = @()
foreach ($l in $r.Links) {
    $href = $l.href
    if (-not $href) { continue }
    if ($href -notmatch "\.pdf") { continue }
    if ($href -notmatch "^https?://") {
        if ($href.StartsWith("/")) {
            $href = "https://www.retio.or.jp$href"
        } else {
            $href = "https://www.retio.or.jp/$href"
        }
    }
    $links += $href
}

$links = $links | Sort-Object -Unique
$out = ".\data\retio_pdf_urls.txt"
$links | Set-Content -LiteralPath $out -Encoding UTF8

Write-Output ("count=" + $links.Count)
Write-Output ("saved=" + $out)
