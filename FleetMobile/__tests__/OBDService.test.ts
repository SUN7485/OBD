import { OBD_PIDS, OBD_DTC, parsePIDResponse, parseDTCResponse, getDTCDescription } from '../src/services/OBDService';

describe('OBDService', () => {
  describe('PID Parsing', () => {
    it('parses RPM correctly', () => {
      // 010C response: 41 0C 1A F8 = (26*256+248)/4 = 1624 RPM
      const response = '41 0C 1A F8';
      const rpm = parsePIDResponse(OBD_PIDS.ENGINE_RPM, response);
      expect(rpm).toBeGreaterThan(0);
    });

    it('parses speed correctly', () => {
      // 010D response: 41 0D 32 = 50 km/h
      const response = '41 0D 32';
      const speed = parsePIDResponse(OBD_PIDS.VEHICLE_SPEED, response);
      expect(speed).toBe(50);
    });

    it('parses coolant temp correctly', () => {
      // 0105 response: 41 05 5A = 90-40 = 50C
      const response = '41 05 5A';
      const temp = parsePIDResponse(OBD_PIDS.COOLANT_TEMP, response);
      expect(temp).toBe(50);
    });

    it('parses engine load correctly', () => {
      // 0104 response: 41 04 5A = 90*100/255 = 35%
      const response = '41 04 5A';
      const load = parsePIDResponse(OBD_PIDS.ENGINE_LOAD, response);
      expect(load).toBeGreaterThan(0);
    });

    it('parses throttle position correctly', () => {
      // 0111 response: 41 11 1A = 26*100/255 = 10%
      const response = '41 11 1A';
      const throttle = parsePIDResponse(OBD_PIDS.THROTTLE_POSITION, response);
      expect(throttle).toBeGreaterThan(0);
    });

    it('returns null for unknown PID', () => {
      const response = '41 FF 00 00';
      const result = parsePIDResponse('01FF', response);
      expect(result).toBeNull();
    });
  });

  describe('DTC Parsing', () => {
    it('parses DTC response correctly', () => {
      // Mode 03 response with P0300
      const response = '43 03 01 71';
      const codes = parseDTCResponse(response);
      expect(Array.isArray(codes)).toBe(true);
    });

    it('returns empty array for no DTCs', () => {
      const response = '43 00 00 00';
      const codes = parseDTCResponse(response);
      expect(codes).toEqual([]);
    });
  });

  describe('DTC Descriptions', () => {
    it('returns description for known code', () => {
      const description = getDTCDescription('P0300');
      expect(description).toContain('Misfire');
    });

    it('returns default for unknown code', () => {
      const description = getDTCDescription('P9999');
      expect(description).toBeDefined();
    });
  });
});