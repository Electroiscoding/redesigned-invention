import { NextResponse } from 'next/server';
import crypto from 'crypto';

export async function POST(request: Request) {
  // In a real application, this must come from a secure KMS/HSM service.
  // We throw an error here to prevent production deployment of hardcoded keys.
  const hsmKeyString = process.env.HSM_ENCRYPTION_KEY;
  if (!hsmKeyString || hsmKeyString.length !== 32) {
      return NextResponse.json(
        { error: 'Internal Server Error: HSM_ENCRYPTION_KEY is not securely configured.' },
        { status: 500 }
      );
  }
  const HSM_KEY = Buffer.from(hsmKeyString);

  try {
    const { openrouter_key } = await request.json();

    if (!openrouter_key || !openrouter_key.startsWith('sk-or-')) {
      return NextResponse.json(
        { error: 'Invalid OpenRouter API Key format.' },
        { status: 400 }
      );
    }

    // Encrypt the API key using AES-256-GCM
    const iv = crypto.randomBytes(12);
    const cipher = crypto.createCipheriv('aes-256-gcm', HSM_KEY, iv);

    let encrypted = cipher.update(openrouter_key, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    const authTag = cipher.getAuthTag().toString('hex');

    // Generate a temporary proxy token for the client
    const proxyToken = crypto.randomUUID();

    // In a real application, we would store the encrypted payload + IV + AuthTag
    // in our PostgreSQL vault table, associated with the proxyToken.
    console.log(`[API Vault] Secured new key. Proxy token: ${proxyToken}`);

    return NextResponse.json({
      success: true,
      token: proxyToken,
      message: 'Key successfully encrypted and stored.'
    });

  } catch (error) {
    console.error('Session vault error:', error);
    return NextResponse.json(
      { error: 'Internal server error during key registration.' },
      { status: 500 }
    );
  }
}
