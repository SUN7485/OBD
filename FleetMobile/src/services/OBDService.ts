/**
 * OBD-II Protocol Service
 * Communicates with ELM327-compatible OBD devices
 */

// OBD-II Mode 01 PIDs
export const OBD_PIDS = {
  SUPPORTED_PIDS: '0100',
  MONITOR_STATUS: '0101',
  FREEZE_DTC: '0102',
  FUEL_SYSTEM_STATUS: '0103',
  ENGINE_LOAD: '0104',
  COOLANT_TEMP: '0105',
  SHORT_TERM_FUEL_TRIM_1: '0106',
  LONG_TERM_FUEL_TRIM_1: '0107',
  SHORT_TERM_FUEL_TRIM_2: '0108',
  LONG_TERM_FUEL_TRIM_2: '0109',
  FUEL_PRESSURE: '010A',
  INTAKE_PRESSURE: '010B',
  ENGINE_RPM: '010C',
  VEHICLE_SPEED: '010D',
  TIMING_ADVANCE: '010E',
  INTAKE_AIR_TEMP: '010F',
  MAF_AIR_FLOW: '0110',
  THROTTLE_POSITION: '0111',
  SECONDARY_AIR_STATUS: '0112',
  O2_SENSORS: '0113',
  RUNTIME_START: '011F',
  DISTANCE_TRAVELED: '0121',
  FUEL_GAUGE_LEVEL: '012F',
  COMMANDED_EGR: '012C',
  FUEL_INJECTION_TIMING: '012D',
  ENGINE_RUN_TIME: '0131',
}

// OBD-II Mode 03 (Read DTCs)
export const OBD_DTC = {
  READ_DTC: '03',
  CLEAR_DTC: '04',
  READ_PENDING_DTC: '07',
}

// PID response parsers
export interface PIDParser {
  bytes: number;
  parse: (data: number[]) => number;
}

export const PID_PARSERS: Record<string, PIDParser> = {
  '0104': { bytes: 1, parse: (data) => data[0] * 100 / 255 },
  '0105': { bytes: 1, parse: (data) => data[0] - 40 },
  '010C': { bytes: 2, parse: (data) => ((data[0] * 256) + data[1]) / 4 },
  '010D': { bytes: 1, parse: (data) => data[0] },
  '010E': { bytes: 1, parse: (data) => data[0] - 128 / 2 },
  '010F': { bytes: 1, parse: (data) => data[0] - 40 },
  '0110': { bytes: 2, parse: (data) => ((data[0] * 256) + data[1]) / 100 },
  '0111': { bytes: 1, parse: (data) => data[0] * 100 / 255 },
  '012F': { bytes: 1, parse: (data) => data[0] * 100 / 255 },
};

export function parsePIDResponse(pid: string, response: string): number | null {
  const parser = PID_PARSERS[pid];
  if (!parser) return null;

  let cleaned = response.replace(/>/g, '').trim();
  const headerMatch = cleaned.match(/^[0-9A-Fa-f]+/);
  if (headerMatch) {
    cleaned = headerMatch[0];
  }

  if (cleaned.length < parser.bytes * 2) return null;

  const bytes: number[] = [];
  for (let i = 0; i < parser.bytes * 2; i += 2) {
    bytes.push(parseInt(cleaned.substr(i, 2), 16));
  }

  return parser.parse(bytes);
}

// DTC code mappings
export const DTC_DESCRIPTIONS: Record<string, string> = {
  // Powertrain codes (P0xxx)
  'P0100': 'Mass Air Flow Circuit Malfunction',
  'P0101': 'Mass Air Flow Circuit Range/Performance',
  'P0102': 'Mass Air Flow Circuit Low Input',
  'P0103': 'Mass Air Flow Circuit High Input',
  'P0171': 'System Too Lean (Bank 1)',
  'P0172': 'System Too Rich (Bank 1)',
  'P0300': 'Random/Multiple Cylinder Misfire Detected',
  'P0301': 'Cylinder 1 Misfire Detected',
  'P0302': 'Cylinder 2 Misfire Detected',
  'P0303': 'Cylinder 3 Misfire Detected',
  'P0304': 'Cylinder 4 Misfire Detected',
  'P0420': 'Catalyst System Efficiency Below Threshold (Bank 1)',
  'P0430': 'Catalyst System Efficiency Below Threshold (Bank 2)',
  'P0440': 'Evaporative Emission Control System Malfunction',
  'P0442': 'Evaporative Emission Control System Leak Detected (small leak)',
  'P0455': 'Evaporative Emission Control System Leak Detected (large leak)',
  'P0500': 'Vehicle Speed Sensor Malfunction',
  'P0505': 'Idle Control System Malfunction',
  'P0507': 'Idle Control System RPM Higher Than Expected',
  'P0600': 'Serial Communication Link Malfunction',
  'P0700': 'Transmission Control System Malfunction',
  'P0715': 'Input/Turbine Speed Sensor Circuit Malfunction',
  // Body codes (B0xxx)
  'B0001': 'Driver Door Ajar Circuit Short to Ground',
  'B0002': 'Driver Door Ajar Circuit Open',
  'B0010': 'Passenger Door Ajar Circuit Short to Ground',
  // Chassis codes (C0xxx)
  'C0035': 'Left Front Wheel Speed Sensor Circuit',
  'C0040': 'Right Front Wheel Speed Sensor Circuit',
}

export function parseDTCResponse(response: string): string[] {
  const codes: string[] = [];
  const cleaned = response.replace(/\s/g, '').replace('>', '');
  
  if (!cleaned.startsWith('43') && !cleaned.startsWith('47')) return codes;
  
  const dataStart = 2;
  for (let i = dataStart; i < cleaned.length - 3; i += 4) {
    const byte1 = cleaned.substr(i, 2);
    const byte2 = cleaned.substr(i + 2, 2);
    if (byte1 === '00' && byte2 === '00') continue;

    const dtcWord = parseInt(byte1 + byte2, 16);
    if (dtcWord === 0) continue;

    const systemCode = (dtcWord >> 14) & 0x03;
    let prefix = 'P';
    if (systemCode === 1) prefix = 'C';
    else if (systemCode === 2) prefix = 'B';
    else if (systemCode === 3) prefix = 'U';

    const dtcNum = dtcWord & 0x3FFF;
    codes.push(`${prefix}${dtcNum.toString(16).toUpperCase().padStart(4, '0')}`);
  }
  
  return codes;
}

export function getDTCDescription(code: string): string {
  return DTC_DESCRIPTIONS[code] || 'Unknown diagnostic trouble code';
}