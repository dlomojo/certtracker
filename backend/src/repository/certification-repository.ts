// ============ AWS SDK v3 DYNAMODB CLIENT ============

import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { 
  DynamoDBDocumentClient, 
  GetCommand, 
  PutCommand, 
  UpdateCommand, 
  DeleteCommand, 
  QueryCommand, 
  BatchWriteCommand 
} from '@aws-sdk/lib-dynamodb';
import { CertificationItem, UserProfileItem, ReminderItem, AnalyticsItem } from '../types';

const dynamoDBClient = new DynamoDBClient({
  region: process.env.AWS_REGION || 'us-east-1',
});

const docClient = DynamoDBDocumentClient.from(dynamoDBClient);
const TABLE_NAME = process.env.DYNAMODB_TABLE || 'CertTracker-Production';

// ============ DATA ACCESS LAYER ============

export class CertificationRepository {
  
  // Get user profile
  async getUserProfile(userId: string): Promise<UserProfileItem | null> {
    try {
      const command = new GetCommand({
        TableName: TABLE_NAME,
        Key: {
          PK: `USER#${userId}`,
          SK: 'PROFILE'
        }
      });
      
      const result = await docClient.send(command);
      return result.Item as UserProfileItem || null;
    } catch (error) {
      console.error('Error getting user profile:', error);
      throw error;
    }
  }

  // Create/Update user profile
  async saveUserProfile(userId: string, profile: Partial<UserProfileItem>): Promise<void> {
    try {
      const now = new Date().toISOString();
      
      const command = new PutCommand({
        TableName: TABLE_NAME,
        Item: {
          PK: `USER#${userId}`,
          SK: 'PROFILE',
          Type: 'USER',
          UserId: userId,
          CreatedAt: profile.CreatedAt || now,
          UpdatedAt: now,
          ...profile
        }
      });
      
      await docClient.send(command);
    } catch (error) {
      console.error('Error saving user profile:', error);
      throw error;
    }
  }

  // Get all certifications for a user
  async getUserCertifications(userId: string): Promise<CertificationItem[]> {
    try {
      const command = new QueryCommand({
        TableName: TABLE_NAME,
        KeyConditionExpression: 'PK = :pk AND begins_with(SK, :sk)',
        ExpressionAttributeValues: {
          ':pk': `USER#${userId}`,
          ':sk': 'CERT#'
        }
      });
      
      const result = await docClient.send(command);
      return (result.Items as CertificationItem[]) || [];
    } catch (error) {
      console.error('Error getting user certifications:', error);
      throw error;
    }
  }

  // Get single certification
  async getCertification(userId: string, certId: string): Promise<CertificationItem | null> {
    try {
      const command = new GetCommand({
        TableName: TABLE_NAME,
        Key: {
          PK: `USER#${userId}`,
          SK: `CERT#${certId}`
        }
      });
      
      const result = await docClient.send(command);
      return result.Item as CertificationItem || null;
    } catch (error) {
      console.error('Error getting certification:', error);
      throw error;
    }
  }

  // Create certification
  async createCertification(userId: string, certification: Omit<CertificationItem, 'PK' | 'SK' | 'Type' | 'CreatedAt' | 'UpdatedAt' | 'GSI1PK' | 'GSI1SK' | 'GSI2PK' | 'GSI2SK'>): Promise<void> {
    try {
      const now = new Date().toISOString();
      const certId = certification.CertId || `cert-${Date.now()}`;
      
      const item: CertificationItem = {
        PK: `USER#${userId}`,
        SK: `CERT#${certId}`,
        Type: 'CERTIFICATION',
        GSI1PK: `STATUS#${certification.Status}`,
        GSI1SK: certification.ExpirationDate,
        GSI2PK: `CATEGORY#${certification.Category}`,
        GSI2SK: certification.ExpirationDate,
        CreatedAt: now,
        UpdatedAt: now,
        ...certification,
        CertId: certId,
        UserId: userId
      };
      
      const command = new PutCommand({
        TableName: TABLE_NAME,
        Item: item
      });
      
      await docClient.send(command);
      
      // Create automatic reminders
      await this.createReminders(userId, certId, certification.ExpirationDate);
    } catch (error) {
      console.error('Error creating certification:', error);
      throw error;
    }
  }

  // Update certification
  async updateCertification(userId: string, certId: string, updates: Partial<CertificationItem>): Promise<void> {
    try {
      const now = new Date().toISOString();
      
      // Build update expression dynamically
      const updateExpressions: string[] = [];
      const expressionAttributeValues: any = {};
      const expressionAttributeNames: any = {};
      
      Object.entries(updates).forEach(([key, value]) => {
        if (key !== 'PK' && key !== 'SK' && key !== 'Type') {
          const attrName = `#${key}`;
          const attrValue = `:${key}`;
          updateExpressions.push(`${attrName} = ${attrValue}`);
          expressionAttributeNames[attrName] = key;
          expressionAttributeValues[attrValue] = value;
        }
      });
      
      // Always update the UpdatedAt timestamp
      updateExpressions.push('#UpdatedAt = :UpdatedAt');
      expressionAttributeNames['#UpdatedAt'] = 'UpdatedAt';
      expressionAttributeValues[':UpdatedAt'] = now;
      
      // Update GSI keys if status or expiration date changed
      if (updates.Status) {
        updateExpressions.push('#GSI1PK = :GSI1PK');
        expressionAttributeNames['#GSI1PK'] = 'GSI1PK';
        expressionAttributeValues[':GSI1PK'] = `STATUS#${updates.Status}`;
      }
      
      if (updates.ExpirationDate) {
        updateExpressions.push('#GSI1SK = :GSI1SK', '#GSI2SK = :GSI2SK');
        expressionAttributeNames['#GSI1SK'] = 'GSI1SK';
        expressionAttributeNames['#GSI2SK'] = 'GSI2SK';
        expressionAttributeValues[':GSI1SK'] = updates.ExpirationDate;
        expressionAttributeValues[':GSI2SK'] = updates.ExpirationDate;
      }
      
      if (updates.Category) {
        updateExpressions.push('#GSI2PK = :GSI2PK');
        expressionAttributeNames['#GSI2PK'] = 'GSI2PK';
        expressionAttributeValues[':GSI2PK'] = `CATEGORY#${updates.Category}`;
      }
      
      const command = new UpdateCommand({
        TableName: TABLE_NAME,
        Key: {
          PK: `USER#${userId}`,
          SK: `CERT#${certId}`
        },
        UpdateExpression: `SET ${updateExpressions.join(', ')}`,
        ExpressionAttributeNames: expressionAttributeNames,
        ExpressionAttributeValues: expressionAttributeValues
      });
      
      await docClient.send(command);
    } catch (error) {
      console.error('Error updating certification:', error);
      throw error;
    }
  }

  // Delete certification
  async deleteCertification(userId: string, certId: string): Promise<void> {
    try {
      const command = new DeleteCommand({
        TableName: TABLE_NAME,
        Key: {
          PK: `USER#${userId}`,
          SK: `CERT#${certId}`
        }
      });
      
      await docClient.send(command);
      
      // Also delete associated reminders
      await this.deleteReminders(userId, certId);
    } catch (error) {
      console.error('Error deleting certification:', error);
      throw error;
    }
  }

  // Create automatic reminders
  async createReminders(userId: string, certId: string, expirationDate: string): Promise<void> {
    try {
      const reminderDays = [30, 60, 90]; // Default reminder schedule
      const expDate = new Date(expirationDate);
      const items = [];
      
      for (const days of reminderDays) {
        const scheduledDate = new Date(expDate);
        scheduledDate.setDate(scheduledDate.getDate() - days);
        
        const reminder: ReminderItem = {
          PK: `USER#${userId}`,
          SK: `REMINDER#${certId}-${days}`,
          Type: 'REMINDER',
          ReminderId: `${certId}-${days}`,
          UserId: userId,
          CertId: certId,
          DaysBeforeExpiration: days,
          ScheduledFor: scheduledDate.toISOString().split('T')[0],
          Sent: false,
          CreatedAt: new Date().toISOString(),
          UpdatedAt: new Date().toISOString()
        };
        
        items.push({ PutRequest: { Item: reminder } });
      }
      
      if (items.length > 0) {
        const command = new BatchWriteCommand({
          RequestItems: {
            [TABLE_NAME]: items
          }
        });
        
        await docClient.send(command);
      }
    } catch (error) {
      console.error('Error creating reminders:', error);
      throw error;
    }
  }

  // Delete reminders for a certification
  async deleteReminders(userId: string, certId: string): Promise<void> {
    try {
      // First, query to get all reminders for this certification
      const queryCommand = new QueryCommand({
        TableName: TABLE_NAME,
        KeyConditionExpression: 'PK = :pk AND begins_with(SK, :sk)',
        ExpressionAttributeValues: {
          ':pk': `USER#${userId}`,
          ':sk': `REMINDER#${certId}`
        }
      });
      
      const result = await docClient.send(queryCommand);
      
      if (result.Items && result.Items.length > 0) {
        const deleteRequests = result.Items.map(item => ({
          DeleteRequest: {
            Key: {
              PK: item.PK,
              SK: item.SK
            }
          }
        }));
        
        const batchCommand = new BatchWriteCommand({
          RequestItems: {
            [TABLE_NAME]: deleteRequests
          }
        });
        
        await docClient.send(batchCommand);
      }
    } catch (error) {
      console.error('Error deleting reminders:', error);
      throw error;
    }
  }

  // Get expiring certifications (using GSI)
  async getExpiringCertifications(beforeDate: string): Promise<CertificationItem[]> {
    try {
      const command = new QueryCommand({
        TableName: TABLE_NAME,
        IndexName: 'GSI1', // Status index
        KeyConditionExpression: 'GSI1PK = :gsi1pk AND GSI1SK <= :expirationDate',
        ExpressionAttributeValues: {
          ':gsi1pk': 'STATUS#active',
          ':expirationDate': beforeDate
        }
      });
      
      const result = await docClient.send(command);
      return (result.Items as CertificationItem[]) || [];
    } catch (error) {
      console.error('Error getting expiring certifications:', error);
      throw error;
    }
  }

  // Get certifications by category (using GSI)
  async getCertificationsByCategory(category: string): Promise<CertificationItem[]> {
    try {
      const command = new QueryCommand({
        TableName: TABLE_NAME,
        IndexName: 'GSI2', // Category index
        KeyConditionExpression: 'GSI2PK = :gsi2pk',
        ExpressionAttributeValues: {
          ':gsi2pk': `CATEGORY#${category}`
        }
      });
      
      const result = await docClient.send(command);
      return (result.Items as CertificationItem[]) || [];
    } catch (error) {
      console.error('Error getting certifications by category:', error);
      throw error;
    }
  }

  // Update analytics
  async updateAnalytics(userId: string): Promise<void> {
    try {
      const certifications = await this.getUserCertifications(userId);
      const currentMonth = new Date().toISOString().slice(0, 7); // YYYY-MM
      
      const analytics: AnalyticsItem = {
        PK: `ANALYTICS#${userId}`,
        SK: `SUMMARY#${currentMonth}`,
        Type: 'ANALYTICS',
        UserId: userId,
        Month: currentMonth,
        TotalCerts: certifications.length,
        ActiveCerts: certifications.filter(c => c.Status === 'active').length,
        ExpiringCerts: certifications.filter(c => c.Status === 'expiring').length,
        ExpiredCerts: certifications.filter(c => c.Status === 'expired').length,
        TotalCost: certifications.reduce((sum, c) => sum + (c.Cost || 0), 0),
        CategoriesCount: {},
        ProvidersCount: {},
        CreatedAt: new Date().toISOString(),
        UpdatedAt: new Date().toISOString()
      };
      
      // Count by categories
      certifications.forEach(cert => {
        analytics.CategoriesCount[cert.Category] = (analytics.CategoriesCount[cert.Category] || 0) + 1;
        analytics.ProvidersCount[cert.Provider] = (analytics.ProvidersCount[cert.Provider] || 0) + 1;
      });
      
      const command = new PutCommand({
        TableName: TABLE_NAME,
        Item: analytics
      });
      
      await docClient.send(command);
    } catch (error) {
      console.error('Error updating analytics:', error);
      throw error;
    }
  }
}