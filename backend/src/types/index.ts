// ============ DYNAMODB SCHEMA DESIGN ============

/*
Production DynamoDB Single-Table Design for CertTracker

Table: CertTracker-Production
Partition Key: PK (String)
Sort Key: SK (String)

Access Patterns:
1. Get user profile: PK=USER#userId, SK=PROFILE
2. Get all user certifications: PK=USER#userId, SK begins_with CERT#
3. Get certification by ID: PK=USER#userId, SK=CERT#certId
4. Get reminders for user: PK=USER#userId, SK begins_with REMINDER#
5. Get expiring certifications (GSI): GSI1PK=STATUS#expiring, GSI1SK=expirationDate
6. Get certifications by category (GSI): GSI2PK=CATEGORY#category, GSI2SK=expirationDate
7. Get analytics data: PK=ANALYTICS#userId, SK=SUMMARY#YYYY-MM
*/

// ============ TYPESCRIPT INTERFACES ============

interface DynamoDBItem {
  PK: string;
  SK: string;
  Type: string;
  CreatedAt: string;
  UpdatedAt: string;
}

interface UserProfileItem extends DynamoDBItem {
  Type: 'USER';
  UserId: string;
  Email: string;
  Name: string;
  Preferences: {
    emailNotifications: boolean;
    reminderDays: number[];
    timezone: string;
  };
}

interface CertificationItem extends DynamoDBItem {
  Type: 'CERTIFICATION';
  CertId: string;
  UserId: string;
  Name: string;
  Provider: string;
  IssueDate: string;
  ExpirationDate: string;
  Status: 'active' | 'expiring' | 'expired' | 'renewed';
  Category: string;
  Priority: 'high' | 'medium' | 'low';
  CredentialId?: string;
  VerificationUrl?: string;
  DocumentUrl?: string;
  RemindersSent: number;
  LastReminderDate?: string;
  RenewalInstructions?: string;
  CPERequired?: number;
  CPECompleted?: number;
  Cost?: number;
  Tags: string[];
  Notes?: string;
  GSI1PK: string; // STATUS#status
  GSI1SK: string; // expirationDate
  GSI2PK: string; // CATEGORY#category
  GSI2SK: string; // expirationDate
}

interface ReminderItem extends DynamoDBItem {
  Type: 'REMINDER';
  ReminderId: string;
  UserId: string;
  CertId: string;
  DaysBeforeExpiration: number;
  ScheduledFor: string;
  Sent: boolean;
  SentAt?: string;
}

interface AnalyticsItem extends DynamoDBItem {
  Type: 'ANALYTICS';
  UserId: string;
  Month: string;
  TotalCerts: number;
  ActiveCerts: number;
  ExpiringCerts: number;
  ExpiredCerts: number;
  TotalCost: number;
  CategoriesCount: { [key: string]: number };
  ProvidersCount: { [key: string]: number };
}

export type { 
  DynamoDBItem,
  UserProfileItem,
  CertificationItem, 
  ReminderItem, 
  AnalyticsItem 
};