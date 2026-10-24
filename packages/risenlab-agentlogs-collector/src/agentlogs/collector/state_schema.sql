BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "Job" (
	"id"	INTEGER,
	"type"	TEXT NOT NULL,
	"status"	TEXT NOT NULL,
	"priority"	INTEGER NOT NULL,
	"parameters"	TEXT NOT NULL,
	"error"	TEXT,
	"resource_id"	INTEGER,
	"created_at"	TEXT NOT NULL,
	"updated_at"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	UNIQUE("type","resource_id"),
	FOREIGN KEY("resource_id") REFERENCES "Resource"("id")
);
CREATE TABLE IF NOT EXISTS "Resource" (
	"id"	INTEGER,
	"type"	TEXT NOT NULL,
	"created_at"	TEXT NOT NULL,
	"updated_at"	TEXT NOT NULL,
	"found"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "ResourceAlias" (
	"id"	INTEGER,
	"resource_id"	INTEGER NOT NULL,
	"type"	TEXT NOT NULL,
	"key"	TEXT NOT NULL,
	"value"	TEXT NOT NULL,
	"created_at"	TEXT NOT NULL,
	"updated_at"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	UNIQUE("type","key","value"),
	UNIQUE("resource_id","key"),
	FOREIGN KEY("resource_id") REFERENCES "Resource"("id")
);
CREATE TABLE IF NOT EXISTS "ResourceMetadata" (
	"id"	INTEGER,
	"resource_id"	INTEGER NOT NULL,
	"key"	TEXT NOT NULL,
	"value"	TEXT,
	"created_at"	INTEGER NOT NULL,
	"updated_at"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	UNIQUE("resource_id","key"),
	FOREIGN KEY("resource_id") REFERENCES "Resource"("id")
);
CREATE TABLE IF NOT EXISTS "ResourceRelation" (
	"id"	INTEGER,
	"type"	TEXT NOT NULL,
	"from_resource_id"	INTEGER NOT NULL,
	"to_resource_id"	INTEGER NOT NULL,
	"created_at"	TEXT NOT NULL,
	"updated_at"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	UNIQUE("type","from_resource_id","to_resource_id"),
	FOREIGN KEY("from_resource_id") REFERENCES "Resource"("id"),
	FOREIGN KEY("to_resource_id") REFERENCES "Resource"
);
CREATE INDEX IF NOT EXISTS "Job.queue" ON "Job" (
	"type",
	"priority"	DESC,
	"id"	ASC
) WHERE "status" = 'queued';
CREATE INDEX IF NOT EXISTS "Job.type_status" ON "Job" (
	"type",
	"status"
);
CREATE INDEX IF NOT EXISTS "Job.resource_id" ON "Job" (
	"resource_id"
);
CREATE INDEX IF NOT EXISTS "Resource.type_id" ON "Resource" (
	"type",
	"id"
);
CREATE INDEX IF NOT EXISTS "ResourceRelation.from_resource_id" ON "ResourceRelation" (
	"from_resource_id",
	"type",
	"to_resource_id"
);
CREATE INDEX IF NOT EXISTS "ResourceRelation.to_resource_id" ON "ResourceRelation" (
	"to_resource_id",
	"type",
	"from_resource_id"
);
COMMIT;
