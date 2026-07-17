using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;

public static class JxpIconTools
{
    private const int DdsHeaderSize = 128;
    private const int IconSize = 57;

    public static string ProcessSheet(
        string sourcePath,
        string[] previewPaths,
        string[] ddsPaths,
        int columns,
        int rows,
        string ddsTemplatePath)
    {
        if (previewPaths.Length != ddsPaths.Length)
            throw new ArgumentException("Preview and DDS path counts differ.");
        if (previewPaths.Length > columns * rows)
            throw new ArgumentException("The grid has fewer cells than requested icons.");

        using (var sourceRaw = new Bitmap(sourcePath))
        using (var source = ToArgb(sourceRaw))
        {
            var reports = new List<string>();
            for (int index = 0; index < previewPaths.Length; index++)
            {
                int column = index % columns;
                int row = index / columns;
                int x0 = column * source.Width / columns;
                int x1 = (column + 1) * source.Width / columns;
                int y0 = row * source.Height / rows;
                int y1 = (row + 1) * source.Height / rows;
                var cell = Rectangle.FromLTRB(x0, y0, x1, y1);
                var crop = FindContentBounds(source, cell, Color.FromArgb(255, 0, 255));

                using (var icon = ExtractIcon(source, crop, Color.FromArgb(255, 0, 255)))
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(previewPaths[index]));
                    Directory.CreateDirectory(Path.GetDirectoryName(ddsPaths[index]));
                    icon.Save(previewPaths[index], ImageFormat.Png);
                    WriteDds(icon, ddsPaths[index], ddsTemplatePath);
                    reports.Add(String.Format(
                        "{0}: cell={1},{2},{3},{4}; crop={5},{6},{7},{8}",
                        Path.GetFileNameWithoutExtension(ddsPaths[index]),
                        cell.X, cell.Y, cell.Width, cell.Height,
                        crop.X, crop.Y, crop.Width, crop.Height));
                }
            }
            return String.Join(Environment.NewLine, reports.ToArray());
        }
    }

    public static void CreatePngContactSheet(
        string[] pngPaths,
        string[] labels,
        int columns,
        string title,
        string outputPath)
    {
        if (pngPaths.Length != labels.Length)
            throw new ArgumentException("Image and label counts differ.");

        const int cellWidth = 112;
        const int cellHeight = 136;
        const int titleHeight = 42;
        int rows = (pngPaths.Length + columns - 1) / columns;
        using (var sheet = new Bitmap(columns * cellWidth, titleHeight + rows * cellHeight, PixelFormat.Format32bppArgb))
        using (var graphics = Graphics.FromImage(sheet))
        using (var titleFont = new Font("Segoe UI", 14, FontStyle.Bold, GraphicsUnit.Pixel))
        using (var labelFont = new Font("Segoe UI", 10, FontStyle.Regular, GraphicsUnit.Pixel))
        using (var titleBrush = new SolidBrush(Color.FromArgb(245, 235, 215)))
        using (var labelBrush = new SolidBrush(Color.FromArgb(225, 218, 205)))
        using (var gridPen = new Pen(Color.FromArgb(70, 62, 57)))
        {
            graphics.Clear(Color.FromArgb(25, 24, 22));
            graphics.InterpolationMode = InterpolationMode.NearestNeighbor;
            graphics.PixelOffsetMode = PixelOffsetMode.Half;
            graphics.DrawString(title, titleFont, titleBrush, 10, 10);

            for (int i = 0; i < pngPaths.Length; i++)
            {
                int column = i % columns;
                int row = i / columns;
                int left = column * cellWidth;
                int top = titleHeight + row * cellHeight;
                graphics.DrawRectangle(gridPen, left, top, cellWidth - 1, cellHeight - 1);
                using (var icon = new Bitmap(pngPaths[i]))
                {
                    graphics.DrawImage(icon, new Rectangle(left + 9, top + 7, 94, 94));
                }
                var textRect = new RectangleF(left + 4, top + 104, cellWidth - 8, 27);
                using (var format = new StringFormat())
                {
                    format.Alignment = StringAlignment.Center;
                    format.LineAlignment = StringAlignment.Near;
                    format.Trimming = StringTrimming.EllipsisCharacter;
                    graphics.DrawString(labels[i], labelFont, labelBrush, textRect, format);
                }
            }

            Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
            sheet.Save(outputPath, ImageFormat.Png);
        }
    }

    public static void CreateDdsContactSheet(
        string[] ddsPaths,
        string[] labels,
        int columns,
        string title,
        string outputPath)
    {
        if (ddsPaths.Length != labels.Length)
            throw new ArgumentException("Image and label counts differ.");

        var temporaryPaths = new string[ddsPaths.Length];
        string tempDirectory = Path.Combine(Path.GetDirectoryName(outputPath), ".reference_png");
        Directory.CreateDirectory(tempDirectory);
        try
        {
            for (int i = 0; i < ddsPaths.Length; i++)
            {
                temporaryPaths[i] = Path.Combine(tempDirectory, i.ToString("D2") + ".png");
                using (var icon = ReadDds(ddsPaths[i]))
                    icon.Save(temporaryPaths[i], ImageFormat.Png);
            }
            CreatePngContactSheet(temporaryPaths, labels, columns, title, outputPath);
        }
        finally
        {
            if (Directory.Exists(tempDirectory))
                Directory.Delete(tempDirectory, true);
        }
    }

    public static string InspectDds(string path)
    {
        byte[] bytes = File.ReadAllBytes(path);
        if (bytes.Length < DdsHeaderSize)
            throw new InvalidDataException(path + " is shorter than a DDS header.");
        int width = BitConverter.ToInt32(bytes, 16);
        int height = BitConverter.ToInt32(bytes, 12);
        int rgbBits = BitConverter.ToInt32(bytes, 88);
        uint redMask = BitConverter.ToUInt32(bytes, 92);
        uint greenMask = BitConverter.ToUInt32(bytes, 96);
        uint blueMask = BitConverter.ToUInt32(bytes, 100);
        uint alphaMask = BitConverter.ToUInt32(bytes, 104);

        int alphaNonzero = 0;
        int alphaPartial = 0;
        int alphaOpaque = 0;
        int alphaMin = 255;
        int alphaMax = 0;
        long colorEnergy = 0;
        for (int offset = DdsHeaderSize; offset + 3 < bytes.Length; offset += 4)
        {
            int b = bytes[offset];
            int g = bytes[offset + 1];
            int r = bytes[offset + 2];
            int a = bytes[offset + 3];
            alphaMin = Math.Min(alphaMin, a);
            alphaMax = Math.Max(alphaMax, a);
            if (a > 0) alphaNonzero++;
            if (a == 255) alphaOpaque++;
            else if (a > 0) alphaPartial++;
            colorEnergy += r + g + b;
        }

        return String.Format(
            "{0}|{1}x{2}|RGBA{3}|masks={4:X8}/{5:X8}/{6:X8}/{7:X8}|bytes={8}|alpha={9}-{10}|nonzero={11}|partial={12}|opaque={13}|color_energy={14}",
            Path.GetFileName(path), width, height, rgbBits,
            redMask, greenMask, blueMask, alphaMask, bytes.Length,
            alphaMin, alphaMax, alphaNonzero, alphaPartial, alphaOpaque, colorEnergy);
    }

    public static Bitmap ReadDds(string path)
    {
        byte[] bytes = File.ReadAllBytes(path);
        if (bytes.Length < DdsHeaderSize || bytes[0] != (byte)'D' || bytes[1] != (byte)'D' || bytes[2] != (byte)'S')
            throw new InvalidDataException(path + " is not a supported DDS file.");
        int width = BitConverter.ToInt32(bytes, 16);
        int height = BitConverter.ToInt32(bytes, 12);
        int rgbBits = BitConverter.ToInt32(bytes, 88);
        if (rgbBits != 32 || bytes.Length < DdsHeaderSize + width * height * 4)
            throw new InvalidDataException(path + " is not an uncompressed 32-bit DDS file.");

        var bitmap = new Bitmap(width, height, PixelFormat.Format32bppArgb);
        int offset = DdsHeaderSize;
        for (int y = 0; y < height; y++)
        {
            for (int x = 0; x < width; x++)
            {
                int b = bytes[offset++];
                int g = bytes[offset++];
                int r = bytes[offset++];
                int a = bytes[offset++];
                bitmap.SetPixel(x, y, Color.FromArgb(a, r, g, b));
            }
        }
        return bitmap;
    }

    private static Bitmap ToArgb(Bitmap source)
    {
        var copy = new Bitmap(source.Width, source.Height, PixelFormat.Format32bppArgb);
        using (var graphics = Graphics.FromImage(copy))
            graphics.DrawImageUnscaled(source, 0, 0);
        return copy;
    }

    private static Rectangle FindContentBounds(Bitmap source, Rectangle cell, Color key)
    {
        int[] xCounts = new int[cell.Width];
        int[] yCounts = new int[cell.Height];
        const int thresholdSquared = 70 * 70;

        for (int y = cell.Top; y < cell.Bottom; y++)
        {
            for (int x = cell.Left; x < cell.Right; x++)
            {
                Color pixel = source.GetPixel(x, y);
                int dr = pixel.R - key.R;
                int dg = pixel.G - key.G;
                int db = pixel.B - key.B;
                if (dr * dr + dg * dg + db * db > thresholdSquared)
                {
                    xCounts[x - cell.Left]++;
                    yCounts[y - cell.Top]++;
                }
            }
        }

        int minimumXOccupancy = Math.Max(4, (int)Math.Round(cell.Height * 0.07));
        int minimumYOccupancy = Math.Max(4, (int)Math.Round(cell.Width * 0.07));
        int left = FirstAtLeast(xCounts, minimumXOccupancy);
        int right = LastAtLeast(xCounts, minimumXOccupancy);
        int top = FirstAtLeast(yCounts, minimumYOccupancy);
        int bottom = LastAtLeast(yCounts, minimumYOccupancy);

        if (left < 0 || right <= left || top < 0 || bottom <= top)
        {
            int insetX = Math.Max(2, cell.Width / 20);
            int insetY = Math.Max(2, cell.Height / 20);
            return Rectangle.FromLTRB(cell.Left + insetX, cell.Top + insetY, cell.Right - insetX, cell.Bottom - insetY);
        }

        var bounds = Rectangle.FromLTRB(
            cell.Left + left,
            cell.Top + top,
            cell.Left + right + 1,
            cell.Top + bottom + 1);
        int padding = Math.Max(2, Math.Min(cell.Width, cell.Height) / 80);
        bounds.Inflate(padding, padding);
        bounds.Intersect(cell);

        int side = Math.Max(bounds.Width, bounds.Height);
        int centerX = bounds.Left + bounds.Width / 2;
        int centerY = bounds.Top + bounds.Height / 2;
        int squareLeft = centerX - side / 2;
        int squareTop = centerY - side / 2;
        squareLeft = Math.Max(cell.Left, Math.Min(squareLeft, cell.Right - side));
        squareTop = Math.Max(cell.Top, Math.Min(squareTop, cell.Bottom - side));
        return new Rectangle(squareLeft, squareTop, Math.Min(side, cell.Width), Math.Min(side, cell.Height));
    }

    private static int FirstAtLeast(int[] values, int minimum)
    {
        for (int i = 0; i < values.Length; i++)
            if (values[i] >= minimum) return i;
        return -1;
    }

    private static int LastAtLeast(int[] values, int minimum)
    {
        for (int i = values.Length - 1; i >= 0; i--)
            if (values[i] >= minimum) return i;
        return -1;
    }

    private static Bitmap ExtractIcon(Bitmap source, Rectangle crop, Color key)
    {
        var icon = new Bitmap(IconSize, IconSize, PixelFormat.Format32bppArgb);
        using (var graphics = Graphics.FromImage(icon))
        {
            graphics.Clear(key);
            graphics.CompositingMode = CompositingMode.SourceCopy;
            graphics.CompositingQuality = CompositingQuality.HighQuality;
            graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
            graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;
            graphics.SmoothingMode = SmoothingMode.HighQuality;
            graphics.DrawImage(source, new Rectangle(0, 0, IconSize, IconSize), crop, GraphicsUnit.Pixel);
        }

        SoftKeyAndGrade(icon, key);
        ReinforceFrame(icon);
        return icon;
    }

    private static void SoftKeyAndGrade(Bitmap icon, Color key)
    {
        var graded = new Color[IconSize, IconSize];
        for (int y = 0; y < IconSize; y++)
        {
            for (int x = 0; x < IconSize; x++)
            {
                Color pixel = icon.GetPixel(x, y);
                int dr = pixel.R - key.R;
                int dg = pixel.G - key.G;
                int db = pixel.B - key.B;
                double distance = Math.Sqrt(dr * dr + dg * dg + db * db);
                double keyFactor = Math.Max(0.0, Math.Min(1.0, (distance - 38.0) / 72.0));
                int alpha = Clamp((int)Math.Round(pixel.A * keyFactor));

                double luminance = pixel.R * 0.2126 + pixel.G * 0.7152 + pixel.B * 0.0722;
                int r = GradeChannel(luminance + (pixel.R - luminance) * 1.05);
                int g = GradeChannel(luminance + (pixel.G - luminance) * 1.05);
                int b = GradeChannel(luminance + (pixel.B - luminance) * 1.05);
                if (keyFactor < 1.0)
                {
                    int spill = (int)Math.Round((1.0 - keyFactor) * 52.0);
                    r = Math.Max(0, r - spill);
                    b = Math.Max(0, b - spill);
                }
                graded[x, y] = Color.FromArgb(alpha, r, g, b);
            }
        }

        for (int y = 0; y < IconSize; y++)
            for (int x = 0; x < IconSize; x++)
                icon.SetPixel(x, y, graded[x, y]);
    }

    private static int GradeChannel(double value)
    {
        return Clamp((int)Math.Round((value - 128.0) * 1.06 + 128.0));
    }

    private static void ReinforceFrame(Bitmap icon)
    {
        using (var graphics = Graphics.FromImage(icon))
        using (var outer = new Pen(Color.FromArgb(255, 52, 12, 16), 1))
        using (var middle = new Pen(Color.FromArgb(240, 105, 31, 30), 1))
        using (var highlight = new Pen(Color.FromArgb(190, 152, 66, 49), 1))
        using (var shadow = new Pen(Color.FromArgb(220, 38, 8, 13), 1))
        {
            graphics.CompositingMode = CompositingMode.SourceOver;
            graphics.SmoothingMode = SmoothingMode.None;
            graphics.DrawRectangle(outer, 0, 0, IconSize - 1, IconSize - 1);
            graphics.DrawRectangle(middle, 1, 1, IconSize - 3, IconSize - 3);
            graphics.DrawLine(highlight, 2, 2, IconSize - 3, 2);
            graphics.DrawLine(highlight, 2, 2, 2, IconSize - 3);
            graphics.DrawLine(shadow, 2, IconSize - 3, IconSize - 3, IconSize - 3);
            graphics.DrawLine(shadow, IconSize - 3, 2, IconSize - 3, IconSize - 3);
        }
    }

    private static int Clamp(int value)
    {
        return Math.Max(0, Math.Min(255, value));
    }

    private static void WriteDds(Bitmap icon, string outputPath, string templatePath)
    {
        byte[] template = File.ReadAllBytes(templatePath);
        if (template.Length < DdsHeaderSize)
            throw new InvalidDataException("DDS template is too short.");

        using (var stream = new FileStream(outputPath, FileMode.Create, FileAccess.Write, FileShare.None))
        using (var writer = new BinaryWriter(stream))
        {
            writer.Write(template, 0, DdsHeaderSize);
            for (int y = 0; y < IconSize; y++)
            {
                for (int x = 0; x < IconSize; x++)
                {
                    Color pixel = icon.GetPixel(x, y);
                    writer.Write(pixel.B);
                    writer.Write(pixel.G);
                    writer.Write(pixel.R);
                    writer.Write(pixel.A);
                }
            }
        }
    }
}
