{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "music-query-env";
  description = "Development environment for music-query application";

  buildInputs = with pkgs; [
    # Python with all required packages
    (python312.withPackages (ps: with ps; [
      flask
      requests
      yt-dlp
      mutagen
      python-dotenv
      beets
      gunicorn
      flasgger
    ]))

    # System dependencies
    ffmpeg                    # Required by yt-dlp for audio processing
    libopus                   # Audio codec support
  ];

  shellHook = ''
    echo "✓ Development environment loaded"
    echo "✓ Python version: $(python --version)"
  '';
}
