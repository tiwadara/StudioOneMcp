// Studio One 5's controlsurfacedevice.js uses PreSonus.SysexBuffer without
// including the file that defines it, so load midiprotocol.js first.
include_file("resource://com.presonus.musicdevices/sdk/midiprotocol.js");
include_file("resource://com.presonus.musicdevices/sdk/controlsurfacedevice.js");

// Nothing to do here: device scripts have no Host object. The work happens in
// ProbeComponent.js, woken by the doorbell note mapped in MCPProbe.surface.xml.
class ProbeDevice extends PreSonus.ControlSurfaceDevice {}

function createProbeDevice() {
    return new ProbeDevice();
}
